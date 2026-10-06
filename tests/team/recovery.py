#!/usr/bin/env python3
"""Execute one dependent product trajectory across an initial session and ten resets."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from evaluate import change_risk, copy_source, grade, json_digest, read_json, state_lock
from probe import (codex_session_models, digest, inside, inventory, metadata, private_directory,
                   route_compliance, run_session, tree_digest, write_json)


REQUIRED_EVENTS = {"checkpointed", "abrupt", "requirement_change", "failed_command",
                   "stale_verification", "dirty_preservation", "live_worker", "completed_worker"}


def specification_digest(manifest):
    return json_digest({key: value for key, value in manifest.items()
                        if key not in ("independent_review", "control_audit")})


def validate(manifest):
    if manifest.get("schema") != 1 or len(manifest.get("phases", [])) != 11:
        raise ValueError("Recovery requires initial session plus exactly ten fresh resets")
    covered = {event for phase in manifest["phases"] for event in phase["events"]}
    if not REQUIRED_EVENTS <= covered:
        raise ValueError("Missing recovery scenarios: " + str(sorted(REQUIRED_EVENTS - covered)))
    if tree_digest(manifest["source"]) != manifest["source_sha256"]:
        raise ValueError("Recovery source changed")
    if not manifest.get("preserved_paths") or not manifest.get("allowed_paths"):
        raise ValueError("Specify preserved dirty paths and allowed writes")
    review = manifest.get("independent_review", {})
    audit = manifest.get("control_audit", {})
    if (review.get("approved") is not True or not review.get("reviewer") or not review.get("findings")
            or review.get("specification_sha256") != specification_digest(manifest)
            or not audit.get("path") or not audit.get("sha256")
            or digest(Path(audit["path"]).read_bytes()) != audit["sha256"]
            or review.get("control_audit_sha256") != audit["sha256"]):
        raise ValueError("Recovery requires a bound independent review and frozen control audit")
    audit_data = read_json(audit["path"])
    if audit_data.get("pass") is not True or audit_data.get("specification_sha256") != specification_digest(manifest):
        raise ValueError("Recovery control audit must pass the exact specification")
    if not manifest.get("route", {}).get("expected_root_models"):
        raise ValueError("Recovery requires expected structured root model identities")
    public_repo = Path(__file__).resolve().parents[2]
    source = Path(manifest["source"])
    for phase in manifest["phases"]:
        if not phase.get("requirements") or not phase.get("grader_files"):
            raise ValueError("Each phase needs external outcome evidence")
        for filename, sha in phase["grader_files"].items():
            if inside(filename, source) or inside(filename, public_repo):
                raise ValueError("Recovery graders must stay outside source and public repository")
            if any(inside(filename, directory) for directory in manifest.get("worker_workspace_roots", [])):
                raise ValueError("Recovery grader overlaps writable worker root")
            if digest(Path(filename).read_bytes()) != sha:
                raise ValueError("Recovery grader changed")
        lifecycle = phase.get("lifecycle", "complete")
        if lifecycle not in ("complete", "retain_after_marker", "interrupt_after_marker"):
            raise ValueError("Unsupported recovery lifecycle")
        if lifecycle != "complete" and (not phase.get("marker") or Path(phase["marker"]).is_absolute()
                                         or ".." in Path(phase["marker"]).parts):
            raise ValueError("Marker must be a relative subject path")
        if "abrupt" in phase["events"] and lifecycle != "interrupt_after_marker" and not phase.get("interrupt_after_seconds"):
            raise ValueError("Abrupt interruption needs an actual process interruption")


def live_receipt(output, route):
    receipt = read_json(output / "receipt.json")
    if receipt.get("status") != "running":
        return receipt
    events = []
    stream = output / "stdout.jsonl"
    for line in stream.read_text(errors="replace").splitlines() if stream.exists() else []:
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            continue
    receipt.update(metadata(events, route["backend"]))
    if route["backend"] == "codex":
        models, evidence = codex_session_models(receipt["session_ids"])
        receipt["root_reported_models"] = sorted(set(receipt["root_reported_models"] or []) | set(models)) or None
        receipt["model_evidence"] = evidence
    receipt["route_compliance"] = route_compliance(receipt, route.get("model"), route["expected_root_models"])
    return receipt


def collect_receipt(output, route, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if (output / "receipt.json").exists():
            receipt = live_receipt(output, route)
            if receipt["status"] != "running":
                return receipt
        time.sleep(0.1)
    raise ValueError("Retained native session did not finish; ownership remains live")


def controlled_session(work, output, prompt, route, phase, allowed_directories):
    lifecycle = phase.get("lifecycle", "complete")
    if lifecycle == "complete":
        return run_session(work, output, prompt, route["backend"], route.get("model"), route.get("effort"),
                           route["concurrency"], phase.get("interrupt_after_seconds"), allowed_directories,
                           route["expected_root_models"], claude_unsandboxed=route.get("claude_unsandboxed", False))
    private_directory(output.parent, work)
    supervisor_root = output.parent.parent / "supervisors"
    supervisor_root.mkdir(exist_ok=True)
    prompt_path = supervisor_root / (output.name + ".prompt.txt")
    prompt_path.write_text(prompt)
    argv = [sys.executable, str(Path(__file__).with_name("probe.py")), "--backend", route["backend"],
            "--workspace", str(work), "--output", str(output), "--prompt", str(prompt_path),
            "--concurrency", str(route["concurrency"])]
    for field in ("model", "effort"):
        if route.get(field):
            argv += ["--" + field, route[field]]
    for identity in route["expected_root_models"]:
        argv += ["--expected-root-model", identity]
    for directory in allowed_directories:
        argv += ["--add-dir", str(directory)]
    if route.get("claude_unsandboxed"):
        argv.append("--claude-unsandboxed")
    marker = work / phase["marker"]
    if marker.exists():
        raise ValueError("Controlled marker already exists; cannot use stale readiness")
    with (supervisor_root / (output.name + ".log")).open("wb") as log:
        supervisor = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.monotonic() + phase.get("marker_timeout_seconds", 600)
    receipt = None
    while time.monotonic() < deadline:
        if (output / "receipt.json").exists():
            receipt = live_receipt(output, route)
            if receipt["status"] != "running":
                raise ValueError("Native root ended before its controlled recovery boundary")
            if marker.exists() and receipt.get("session_ids") and receipt.get("process_pid"):
                break
        if supervisor.poll() is not None:
            raise ValueError("Native supervisor exited before durable boundary")
        time.sleep(0.1)
    else:
        if receipt and receipt.get("process_pid"):
            os.killpg(receipt["process_pid"], signal.SIGTERM)
        raise ValueError("Durable boundary not reached; operational interruption, not product success")
    receipt["supervisor_pid"] = supervisor.pid
    receipt["durable_marker_sha256"] = digest(marker.read_bytes())
    if lifecycle == "interrupt_after_marker":
        os.killpg(receipt["process_pid"], signal.SIGTERM)
        finished = collect_receipt(output, route, 30)
        finished["controlled_interruption"] = True
        finished["durable_marker_sha256"] = receipt["durable_marker_sha256"]
        write_json(output / "receipt.json", finished)
        return finished
    write_json(output / "retained.json", receipt)
    return receipt


def prepare(args):
    manifest = read_json(args.manifest)
    validate(manifest)
    root = private_directory(args.output, Path(__file__).resolve().parents[2])
    if (root / "recovery.json").exists():
        raise ValueError("Recovery trajectory already exists")
    work = root / "subject"
    copy_source(manifest["source"], work)
    for directory in manifest.get("worker_workspace_roots", []):
        Path(directory).mkdir(parents=True, exist_ok=True)
        if inside(root / "sessions", directory) or inside(directory, root / "sessions") or inside(work, directory):
            raise ValueError("Worker roots must be disjoint from integration and private receipts")
    state = {"schema": 1, "manifest": manifest, "manifest_sha256": json_digest(manifest),
             "workspace": str(work), "before": inventory(work), "phases": [],
             "native_compaction_observed": False, "full_workflow_usage": None}
    write_json(root / "recovery.json", state)
    print(root / "recovery.json")
    return True


def step(args):
    state = read_json(args.state)
    manifest = state["manifest"]
    validate(manifest)
    if json_digest(manifest) != state["manifest_sha256"]:
        raise ValueError("Recovery manifest changed")
    index = len(state["phases"])
    if index >= 11:
        raise ValueError("All eleven sessions are already recorded")
    if state["phases"] and not state["phases"][-1]["pass"]:
        raise ValueError("Prior phase failed; diagnose and prepare a new reviewed trajectory")
    phase, route = manifest["phases"][index], manifest["route"]
    work = Path(state["workspace"])
    output = args.state.parent / "sessions" / str(index)
    # A new process is used for every phase. No CLI resume, fork, or conversation replay.
    prompt = ("This is a fresh session continuing the same product task. Recover current requirements, "
              "worker ownership, facts, and next actions from the task files and source. "
              "Check observed live workers before launching replacements; preserve unrelated dirty work. "
              "Do not read evaluation artifacts or prior session transcripts.\n\n"
              + manifest["brief"] + "\n\nCurrent phase instruction:\n" + phase["prompt"]
              + "\nExecution contract:\n" + json.dumps(route, sort_keys=True))
    started = time.monotonic()
    # Journal before any paid launch; a later exception must not erase an attempt.
    state["phases"].append({"phase": index, "reset": index > 0, "events": phase["events"],
                            "status": "running", "pass": False, "session_ids": [],
                            "receipt": str(output / "receipt.json"),
                            "started_utc": datetime.now(timezone.utc).isoformat(),
                            "retained_session": phase.get("lifecycle") == "retain_after_marker"})
    write_json(args.state, state)
    worker_roots = manifest.get("worker_workspace_roots", [])
    prompt += "\nPermitted isolated worker roots: " + json.dumps(worker_roots)
    receipt = controlled_session(work, output, prompt, route, phase, worker_roots)
    observations_path = work / ".sdlc-flow/recovery/runner-observations.json"
    observations_path.parent.mkdir(parents=True, exist_ok=True)
    observations = read_json(observations_path) if observations_path.exists() else {"sessions": {}}
    observations["sessions"][str(index)] = {key: receipt.get(key) for key in
        ("session_ids", "process_pid", "supervisor_pid", "status", "root_reported_models", "route_compliance")}
    write_json(observations_path, observations)
    collected = []
    for prior in phase.get("collect_prior_sessions", []):
        if not isinstance(prior, int) or not 0 <= prior < index:
            raise ValueError("Collection must reference an earlier retained session")
        prior_receipt = collect_receipt(args.state.parent / "sessions" / str(prior), route,
                                        phase.get("collection_timeout_seconds", 600))
        if prior_receipt["status"] != "completed":
            raise ValueError("Retained native root failed after release")
        collected.append(prior)
        state["phases"][prior]["retained_session_collected"] = True
    check = grade(phase, work, output / "phase-grade.json")
    risk = change_risk(manifest, state["before"], inventory(work))
    previous_ids = {session for old in state["phases"] for session in old["session_ids"]}
    session_ids = receipt["session_ids"]
    fresh_proven = bool(session_ids) and not previous_ids.intersection(session_ids)
    expected_interruption = "abrupt" in phase["events"]
    lifecycle = phase.get("lifecycle", "complete")
    lifecycle_ok = ((receipt.get("timed_out") or receipt.get("controlled_interruption")) if expected_interruption
                    else receipt["status"] == ("running" if lifecycle == "retain_after_marker" else "completed"))
    row = {"phase": index, "reset": index > 0, "events": phase["events"],
           "session_ids": session_ids, "fresh_session_proven": fresh_proven,
           "receipt": str(output / "receipt.json"), "checks": check, "change_risk": risk,
           "verified_source_sha256": check["source_sha256"],
           "retained_session": lifecycle == "retain_after_marker", "collected_prior_sessions": collected,
           "wall_seconds_including_validation": time.monotonic() - started,
           "pass": lifecycle_ok and fresh_proven and receipt["route_compliance"]["pass"] and check["pass"] and risk["pass"]}
    row["started_utc"] = state["phases"][index]["started_utc"]
    row["status"] = "verified" if row["pass"] else "failed"
    state["phases"][index] = row
    write_json(args.state, state)
    print(json.dumps(row, indent=2))
    return row["pass"]


def report(args):
    state = read_json(args.state)
    specification_errors = []
    try:
        if json_digest(state["manifest"]) != state["manifest_sha256"]:
            raise ValueError("Recovery manifest changed")
        validate(state["manifest"])
    except (ValueError, OSError, KeyError) as exc:
        specification_errors.append(str(exc))
    phases = state["phases"]
    current_source = tree_digest(state["workspace"])
    evidence_current = bool(phases) and phases[-1].get("verified_source_sha256") == current_source
    native_roots_finished = True
    for index, phase in enumerate(phases):
        receipt_path = args.state.parent / "sessions" / str(index) / "receipt.json"
        receipt = read_json(receipt_path) if receipt_path.exists() else {}
        expected_interruption = "abrupt" in phase["events"]
        terminal = (bool(receipt.get("controlled_interruption") or receipt.get("timed_out"))
                    if expected_interruption else receipt.get("status") == "completed")
        native_roots_finished = native_roots_finished and terminal
    actual_receipts = []
    for path in sorted((args.state.parent / "sessions").glob("*/receipt.json")):
        receipt = read_json(path)
        actual_receipts.append({"path": str(path), "status": receipt.get("status", "unknown"),
                                "session_ids": receipt.get("session_ids", []),
                                "duration_seconds": receipt.get("duration_seconds"),
                                "reported_usage": receipt.get("reported_usage"),
                                "retained": (path.parent / "retained.json").exists()})
    known_durations = [r["duration_seconds"] for r in actual_receipts if r["duration_seconds"] is not None]
    expected_receipts = {str(args.state.parent / "sessions" / str(index) / "receipt.json") for index in range(len(phases))}
    receipts_accounted = {r["path"] for r in actual_receipts} == expected_receipts
    result = {"planned_sessions": 11, "planned_resets": 10, "completed_sessions": sum(row.get("status") == "verified" for row in phases),
              "verified_resets": sum(row["reset"] and row["pass"] for row in phases),
              "pass": not specification_errors and len(phases) == 11 and evidence_current and native_roots_finished and receipts_accounted
                         and all(row["pass"] and (not row.get("retained_session")
                         or row.get("retained_session_collected")) for row in phases),
              "specification_current": not specification_errors,
              "specification_errors": specification_errors,
              "final_evidence_current": evidence_current,
              "current_source_sha256": current_source,
              "all_native_root_receipts_terminal": native_roots_finished,
              "actual_session_receipts": actual_receipts,
              "actual_session_receipt_count": len(actual_receipts),
              "recorded_phase_attempt_count": len(phases),
              "all_actual_receipts_accounted": receipts_accounted,
              "observed_cli_seconds_including_failed_sessions": sum(known_durations) if known_durations else None,
              "cli_duration_receipts_complete": len(known_durations) == len(actual_receipts) and bool(actual_receipts),
              "observed_wall_seconds_including_validation": (sum(row["wall_seconds_including_validation"] for row in phases)
                  if phases and all("wall_seconds_including_validation" in row for row in phases) else None),
              "full_workflow_usage": None, "full_workflow_cost_usd": None,
              "native_compaction_observed": False,
              "classification": "native fresh-session recovery; not native compaction",
              "limitations": ["External phase checks must prove live-worker identity, completed result recovery, and lack of duplication",
                              "Descendant and provider-internal accounting may be unavailable"]}
    write_json(args.state.parent / "recovery-report.json", result)
    print(json.dumps(result, indent=2))
    return result["pass"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(func=prepare)
    for name, function in (("step", step), ("report", report)):
        p = commands.add_parser(name)
        p.add_argument("--state", type=Path, required=True)
        p.set_defaults(func=function)
    args = parser.parse_args()
    try:
        if hasattr(args, "state"):
            with state_lock(args.state):
                passed = args.func(args)
        else:
            passed = args.func(args)
    except (ValueError, OSError, KeyError) as exc:
        if args.command == "step" and args.state.exists():
            failed_state = read_json(args.state)
            if failed_state.get("phases") and failed_state["phases"][-1].get("status") == "running":
                failed_state["phases"][-1].update({"status": "failed", "pass": False,
                                                  "error": str(exc),
                                                  "failed_utc": datetime.now(timezone.utc).isoformat()})
                write_json(args.state, failed_state)
        parser.exit(2, str(exc) + "\n")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
