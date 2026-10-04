#!/usr/bin/env python3
"""Audited two-task, two-arm, two-repetition pilot with private outcome checks."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from probe import digest, inside, inventory, private_directory, run_session, tree_digest, write_json


def read_json(path):
    return json.loads(Path(path).read_text())


def json_digest(value):
    return digest(json.dumps(value, sort_keys=True).encode())


@contextmanager
def state_lock(path):
    """Serialize evaluator mutations; model-native workers remain parallel."""
    with Path(path).with_suffix(".lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another evaluator owns this state") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def load_manifest(path, tasks_only=False):
    path = Path(path).resolve()
    manifest = read_json(path)
    if manifest.get("schema") != 1 or len(manifest.get("tasks", [])) != 2:
        raise ValueError("Pilot requires schema 1 and exactly two real-source tasks")
    if not tasks_only and set(manifest.get("arms", {})) != {"candidate", "dev"}:
        raise ValueError("Pilot compares exactly candidate and dev")
    if len({task["id"] for task in manifest["tasks"]}) != 2:
        raise ValueError("Task IDs must be distinct")
    for arm in manifest.get("arms", {}).values():
        skill = Path(arm["skill"]).resolve()
        if not (skill / "SKILL.md").is_file() or tree_digest(skill) != arm["sha256"]:
            raise ValueError("Workflow changed or SKILL.md missing; freeze again")
    if not tasks_only:
        route = manifest["route"]
        if route["backend"] not in ("codex", "claude") or route["concurrency"] < 1:
            raise ValueError("Unsupported native route")
        if not isinstance(route.get("worker_models"), dict) or not route.get("tools_contract"):
            raise ValueError("Freeze worker model map and effective tool contract")
        if not route.get("expected_root_models"):
            raise ValueError("Freeze expected structured host root-model identities")
        compatibility = manifest.get("compatibility", {})
        if (compatibility.get("approved") is not True or compatibility.get("missing_required_skills") != []
                or not compatibility.get("neutral_instruction")):
            raise ValueError("Review shared host adaptation and resolve mandatory workflow dependencies before scoring")
        for item in compatibility.get("support_skills", {}).values():
            if tree_digest(item["path"]) != item["sha256"]:
                raise ValueError("Shared workflow dependency changed")
    for task in manifest["tasks"]:
        if not task["id"].replace("-", "").isalnum():
            raise ValueError("Task ID must contain only letters, digits, hyphens")
        source = Path(task["source"]).resolve()
        if tree_digest(source) != task["source_sha256"]:
            raise ValueError("Task source changed")
        if not task.get("provenance", {}).get("upstream") or not task["provenance"].get("revision"):
            raise ValueError("Real upstream source and pinned revision required")
        if not task.get("requirements") or len(set(task["requirements"])) != len(task["requirements"]):
            raise ValueError("Unique acceptance IDs required")
        if not task.get("review_requirements"):
            raise ValueError("Explicit independent outcome-review requirements required")
        if not task.get("allowed_paths") or not isinstance(task.get("preserved_paths"), list):
            raise ValueError("Allowed writes and preserved paths must be explicit")
        if not task.get("baseline_failures") or not set(task["baseline_failures"]) <= set(task["requirements"]):
            raise ValueError("Baseline must fail at least one named required outcome")
        for filename, sha in task["grader_files"].items():
            private = Path(filename).resolve()
            if inside(private, source) or inside(private, Path(__file__).resolve().parents[2]):
                raise ValueError("Private grader must stay outside subject and public repo")
            if digest(private.read_bytes()) != sha:
                raise ValueError("Private grader changed")
        if not task["grader_argv"] or not any("{workspace}" in value for value in task["grader_argv"]):
            raise ValueError("Grader must take explicit subject workspace")
    return manifest


def grade(task, workspace, output):
    """Each outcome is a bool; a crash/empty result never counts as expected failure."""
    output = Path(output)
    argv = [value.replace("{python}", sys.executable).replace("{workspace}", str(Path(workspace).resolve()))
            for value in task["grader_argv"]]
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=workspace, capture_output=True, text=True,
                                timeout=task.get("grader_timeout_seconds", 120))
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
        decoded = json.loads(stdout)
        checks = decoded.get("checks", {})
        valid = (set(checks) == set(task["requirements"])
                 and all(type(value) is bool for value in checks.values())
                 and decoded.get("errors") == [] and returncode in (0, 1)
                 and (returncode == 0) == all(checks.values()))
        error = None if valid else "Grader schema, acceptance IDs, errors, or exit code inconsistent"
    except (OSError, subprocess.TimeoutExpired, ValueError, AttributeError) as exc:
        stdout, stderr, returncode, checks, valid = "", str(exc), None, {}, False
        error = "Grader infrastructure error: " + str(exc)
    evidence = {"valid": valid, "pass": valid and all(checks.values()), "checks": checks,
                "error": error, "returncode": returncode, "argv": argv,
                "stdout": stdout, "stderr": stderr, "duration_seconds": time.monotonic() - start,
                "source_sha256": tree_digest(workspace), "grader_files": task["grader_files"]}
    write_json(output, evidence)
    return evidence


def copy_source(source, destination):
    shutil.copytree(source, destination, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    # Links outside the disposable subject could leak hidden controls or mutate real work.
    for directory, dirs, files in __import__("os").walk(destination, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            if path.is_symlink() and not inside(path.resolve(), destination):
                raise ValueError("Source contains external symlink: " + str(path))


def allowed(path, prefixes):
    return any(path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")
               for prefix in prefixes)


def git_output(workspace, *arguments):
    result = subprocess.run(["git", "-C", str(workspace), *arguments], capture_output=True, text=True)
    if result.returncode:
        raise ValueError("Git setup/check failed: " + result.stderr)
    return result.stdout.strip()


def prepare_subject(task, work):
    repository = task.get("provenance", {}).get("local_repository")
    if repository:
        result = subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(repository), str(work)],
                                capture_output=True, text=True)
        if result.returncode:
            raise ValueError("Cannot clone pinned real repository: " + result.stderr)
        git_output(work, "checkout", "--quiet", "--detach", task["provenance"]["revision"])
        git_output(work, "remote", "set-url", "origin", task["provenance"]["upstream"])
        source = Path(task["source"])
        before, desired = inventory(work), inventory(source)
        for name in set(before) - set(desired):
            (work / name).unlink()
        for name, identity in desired.items():
            if before.get(name) == identity:
                continue
            original, target = source / name, work / name
            if original.is_symlink() and not inside(original.resolve(), source):
                raise ValueError("External symlink in dirty overlay")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or (original.is_symlink() and target.exists()):
                target.unlink()
            if original.is_symlink():
                target.symlink_to(os.readlink(original))
            else:
                shutil.copy2(original, target)
    else:
        raise ValueError("Pilot requires a pinned local real repository to preserve Git identity and dirty overlay")


def change_risk(task, before, after):
    changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    prohibited = [path for path in changed if not allowed(path, task["allowed_paths"])]
    preserved = [path for path in changed if allowed(path, task["preserved_paths"])]
    return {"changed_paths": changed, "out_of_scope_paths": prohibited,
            "preserved_path_changes": preserved, "pass": not prohibited and not preserved}


def worker_route_compliance(route, receipt):
    if not route.get("require_worker_identity"):
        return {"pass": True, "status": "not_required_by_limited_profile",
                "heterogeneous_claim": False}
    children = receipt.get("native_descendants", [])
    allowed_models = set(route["worker_models"].values())
    observed = {model for child in children for model in (child.get("reported_models") or [])}
    complete = bool(children) and all(child.get("reported_models") for child in children)
    matches = complete and all(set(child["reported_models"]) <= allowed_models and
        (not child.get("requested_model") or set(child["reported_models"]) == {child["requested_model"]})
        for child in children)
    # Role-to-child causality is a mandatory independent per-run review below;
    # model-set equality alone must never establish that assignment mapping.
    review_declared = "ROUTE" in route.get("review_requirement_ids", [])
    return {"pass": bool(matches and allowed_models <= observed and review_declared),
            "status": "observed_pending_role_review" if matches and allowed_models <= observed else "unmet",
            "required_models": sorted(allowed_models), "observed_models": sorted(observed),
            "children": children, "role_assignment_review_required": True}


def audit(args):
    manifest = load_manifest(args.manifest, args.tasks_only)
    out = private_directory(args.output, Path(__file__).resolve().parents[2])
    if (out / "audit.json").exists():
        raise ValueError("Audit already exists; use a fresh directory")
    results = []
    for task in manifest["tasks"]:
        required = set(task["requirements"])
        controls = [{"id": "baseline", "source": task["source"],
                     "expected": {key: key not in task["baseline_failures"] for key in required}}] + task["controls"]
        positive = any(set(c["expected"]) == required and all(c["expected"].values()) for c in task["controls"])
        covered = {key for c in task["controls"] for key, passed in c["expected"].items() if passed is False}
        if not positive or not required <= covered:
            raise ValueError("Audit needs a passing control and targeted failing controls for every acceptance ID")
        for index, control in enumerate(controls):
            source = Path(control["source"]).resolve()
            if index and tree_digest(source) != control["sha256"]:
                raise ValueError("Control source changed")
            with tempfile.TemporaryDirectory(prefix="sdlc-audit-") as temporary:
                subject = Path(temporary) / "subject"
                copy_source(source, subject)
                result = grade(task, subject, out / f"{task['id']}-{index}.json")
            results.append({"task": task["id"], "control": control["id"],
                            "expected": control["expected"], "actual": result["checks"],
                            "pass": result["valid"] and result["checks"] == control["expected"]})
    receipt = {"schema": 1, "manifest_sha256": json_digest(manifest), "controls": results,
               "pass": all(row["pass"] for row in results),
               "independent_review_required": True}
    write_json(out / "audit.json", receipt)
    print(json.dumps({"pass": receipt["pass"], "controls": len(results), "receipt": str(out / "audit.json")}))
    return receipt["pass"]


def prepare(args):
    manifest = load_manifest(args.manifest)
    audited, reviewed = read_json(args.audit), read_json(args.review)
    if (audited.get("manifest_sha256") != json_digest(manifest) or not audited.get("pass")
            or reviewed.get("audit_sha256") != digest(args.audit.read_bytes())
            or reviewed.get("manifest_sha256") != json_digest(manifest)
            or reviewed.get("approved") is not True or not reviewed.get("reviewer")
            or not reviewed.get("findings")):
        raise ValueError("Passing control audit and independent review bound to exact manifest required")
    out = private_directory(args.output, Path(__file__).resolve().parents[2])
    if (out / "pilot.json").exists():
        raise ValueError("Pilot exists; use a fresh private output root")
    runs = []
    for task in manifest["tasks"]:
        # Counterbalance the two repetitions while keeping every run a fresh session.
        for repeat in (1, 2):
            for arm in (("candidate", "dev") if repeat == 1 else ("dev", "candidate")):
                name = f"{task['id']}-{repeat}-{arm}"
                work = out / "subjects" / name
                workers = out / "worker-workspaces" / name
                workers.mkdir(parents=True)
                work.parent.mkdir(exist_ok=True)
                prepare_subject(task, work)
                if tree_digest(work) != task["source_sha256"]:
                    raise ValueError("Copy changed initial snapshot")
                skill = manifest["arms"][arm]
                copy_source(skill["skill"], work / ".evaluation-workflow")
                compatibility = manifest["compatibility"]
                for alias, support in compatibility.get("support_skills", {}).items():
                    if "/" in alias or alias in (".", ".."):
                        raise ValueError("Invalid dependency alias")
                    destination = work / ".evaluation-support" / alias
                    destination.parent.mkdir(exist_ok=True)
                    copy_source(support["path"], destination)
                prompt = ("Use the workflow in .evaluation-workflow/SKILL.md to complete this task. "
                          "The workflow and support skills are read-only. The subject workspace and the "
                          "explicit worker workspace base below are allowed. Other external reads are limited "
                          "to installed runtime/CLI tools. Do not inspect sibling runs or evaluation artifacts. "
                          "Use fresh native workers when delegation is available; do not launch an external provider. "
                          "Preserve unrelated dirty files. Do not commit, publish, or modify global configuration.\n\n"
                          + task["brief"] + "\n\nAcceptance IDs: " + ", ".join(task["requirements"])
                          + "\nExecution contract (identical for both workflows):\n"
                          + json.dumps(manifest["route"], sort_keys=True)
                          + "\nShared reviewed host adaptation:\n" + compatibility["neutral_instruction"]
                          + "\nFrozen support skill aliases: " + json.dumps(sorted(compatibility.get("support_skills", {})))
                          + "\nIntegration workspace: " + str(work)
                          + "\nRead-only workflow entrypoint: " + str(work / ".evaluation-workflow/SKILL.md")
                          + "\nPermitted isolated worker workspace base (precreated and granted via --add-dir): " + str(workers)
                          + "\nEach writer must own a separate non-overlapping copy/worktree beneath that base; "
                          "carry the agreed source and relevant dirty overlay; do not use source hardlinks. "
                          "Return verified changes to the integration workspace. Use versioned task packets for shared context."
                          + "\nAllowed write paths: " + json.dumps(task["allowed_paths"])
                          + "\nPreserved paths: " + json.dumps(task["preserved_paths"]) + "\n")
                prompt_path = out / (name + ".prompt.txt")
                prompt_path.write_text(prompt)
                runs.append({"id": name, "task": task["id"], "repeat": repeat, "arm": arm,
                             "workspace": str(work), "prompt": str(prompt_path),
                             "worker_workspace_base": str(workers),
                             "prompt_sha256": digest(prompt.encode()), "before": inventory(work),
                             "base_commit": git_output(work, "rev-parse", "HEAD"),
                             "initial_git_status": git_output(work, "status", "--porcelain=v1", "--untracked-files=all"),
                             "status": "pending", "attempts": []})
    state = {"schema": 1, "manifest": manifest, "manifest_sha256": json_digest(manifest),
             "audit": audited, "review": reviewed, "runs": runs,
             "planned_attempts": 8, "broad_bank_planned_attempts": 40,
             "broad_bank_allowed": False}
    write_json(out / "pilot.json", state)
    print(out / "pilot.json")
    return True


def run_one(args):
    state = read_json(args.pilot)
    manifest = state["manifest"]
    if json_digest(manifest) != state["manifest_sha256"]:
        raise ValueError("Frozen manifest changed")
    # Recheck private assessment/skill identities at every launch.
    transient = args.pilot.parent / "frozen-manifest.json"
    write_json(transient, manifest)
    load_manifest(transient)
    run = next(row for row in state["runs"] if row["id"] == args.run)
    if run.get("objective_pass"):
        raise ValueError("Independently accepted runs are immutable")
    work = Path(run["workspace"])
    if digest(Path(run["prompt"]).read_bytes()) != run["prompt_sha256"]:
        raise ValueError("Prompt changed")
    if not run["attempts"] and inventory(work) != run["before"]:
        raise ValueError("Subject changed before first attempt")
    if run["attempts"] and not args.retry_reason:
        raise ValueError("Retries require an explicit observed cause; prior usage remains counted")
    route = manifest["route"]
    root = args.pilot.parent / "receipts" / run["id"]
    root.mkdir(parents=True, exist_ok=True)
    attempt_path = root / str(len(run["attempts"]) + 1)
    run["attempts"].append({"path": str(attempt_path), "retry_reason": args.retry_reason})
    run["status"] = "running"
    run.setdefault("started_utc", datetime.now(timezone.utc).isoformat())
    write_json(args.pilot, state)
    receipt = run_session(work, attempt_path, Path(run["prompt"]).read_text(), route["backend"],
                          route.get("model"), route.get("effort"), route["concurrency"], args.timeout,
                          [Path(run["worker_workspace_base"])], route["expected_root_models"])
    task = next(t for t in manifest["tasks"] if t["id"] == run["task"])
    snapshot = root / f"snapshot-{len(run['attempts'])}"
    copy_source(work, snapshot)
    if inventory(snapshot) != inventory(work):
        raise ValueError("Subject changed while freezing")
    risk = change_risk(task, run["before"], inventory(snapshot))
    risk["head_preserved"] = git_output(work, "rev-parse", "HEAD") == run["base_commit"]
    risk["staged_paths"] = git_output(work, "diff", "--cached", "--name-only").splitlines()
    risk["pass"] = risk["pass"] and risk["head_preserved"] and not risk["staged_paths"]
    result = grade(task, snapshot, root / f"grade-{len(run['attempts'])}.json")
    worker_routes = worker_route_compliance(route, receipt)
    automated_pass = (receipt["status"] == "completed" and receipt["route_compliance"]["pass"]
                      and worker_routes["pass"] and result["pass"] and risk["pass"])
    run.update({"status": "completed" if receipt["status"] == "completed" else "failed",
                "grade": result, "change_risk": risk, "snapshot": str(snapshot),
                "automated_pass": automated_pass, "objective_pass": False,
                "worker_route_compliance": worker_routes,
                "review_status": "pending", "review_requirements": task["review_requirements"]})
    write_json(args.pilot, state)
    print(json.dumps({key: run[key] for key in ("id", "status", "objective_pass", "change_risk")}))
    return automated_pass


def accept_review(args):
    state = read_json(args.pilot)
    run = next(row for row in state["runs"] if row["id"] == args.run)
    review = read_json(args.review)
    if not run.get("automated_pass"):
        raise ValueError("Cannot accept a failed or incomplete automated outcome")
    current_hash = tree_digest(run["snapshot"])
    if (current_hash != run["grade"]["source_sha256"] or review.get("source_sha256") != current_hash
            or review.get("manifest_sha256") != state["manifest_sha256"]
            or review.get("run") != run["id"] or not review.get("reviewer")
            or review.get("independent_context") is not True
            or review.get("approved") is not True
            or set(review.get("checks", {})) != set(run["review_requirements"])
            or any(value is not True for value in review["checks"].values())
            or not review.get("evidence")):
        raise ValueError("Independent review must approve all supplemental outcomes on the exact frozen source")
    run.update({"review_status": "accepted", "outcome_review": review, "objective_pass": True,
                "accepted_utc": datetime.now(timezone.utc).isoformat()})
    write_json(args.pilot, state)
    print(json.dumps({"run": run["id"], "objective_pass": True}))
    return True


def report(args):
    state = read_json(args.pilot)
    rows = []
    for run in state["runs"]:
        frozen_evidence_current = (bool(run.get("snapshot")) and Path(run["snapshot"]).is_dir()
                                   and tree_digest(run["snapshot"]) == run.get("grade", {}).get("source_sha256"))
        receipts = [read_json(Path(attempt["path"]) / "receipt.json") for attempt in run["attempts"]
                    if (Path(attempt["path"]) / "receipt.json").exists()]
        rows.append({"id": run["id"], "arm": run["arm"], "status": run["status"],
                     "objective_pass": run.get("objective_pass", False) and frozen_evidence_current,
                     "frozen_evidence_current": frozen_evidence_current,
                     "attempts": len(run["attempts"]),
                     "observed_wall_seconds_including_retries": sum(r["duration_seconds"] for r in receipts if "duration_seconds" in r),
                     "full_workflow_wall_seconds": None, "full_workflow_usage": None,
                     "full_workflow_cost_usd": None,
                     "time_to_reviewed_outcome_seconds": ((datetime.fromisoformat(run["accepted_utc"])
                         - datetime.fromisoformat(run["started_utc"])).total_seconds()
                         if run.get("accepted_utc") else None),
                     "reported_models": sorted({m for r in receipts for m in (r.get("reported_models") or [])}) or None})
    objective_pass = len(rows) == 8 and all(row["status"] == "completed" and row["objective_pass"] for row in rows)
    result = {"planned_pilot_attempts": 8, "runs": rows,
              "pilot_objectives_pass": objective_pass,
              "broad_bank_planned_attempts": 40,
              "broad_bank_allowed": False,
              "remaining_gates": (["Eight complete passing matched attempts"] if not objective_pass else [])
              + ["Independent integrated outcome review", "Native heterogeneous overlap evidence",
                 "Ten fresh-session recovery resets", "Observed route/concurrency compliance",
                 "Complete descendant timing and usage or explicitly limited performance claims"],
              "performance_claim": "Not established; missing full-workflow telemetry remains unknown"}
    write_json(args.pilot.parent / "report.json", result)
    print(json.dumps(result, indent=2))
    return objective_pass


def selftest(_):
    """Mechanical product gate: two correct slices fail when composed."""
    with tempfile.TemporaryDirectory(prefix="sdlc-integration-") as temporary:
        root = Path(temporary)
        # Feature A exports a lazy stream; feature B's preview consumes that stream.
        (root / "product.py").write_text("def export(rows):\n    return (str(row) for row in rows)\n\ndef preview(rows):\n    return list(rows)[:1]\n\ndef deliver(rows):\n    data = export(rows)\n    preview(data)\n    return list(data)\n")
        (root / "checks.py").write_text("import json\nfrom product import export, preview, deliver\nc = {'A': list(export([1, 2])) == ['1', '2'], 'B': preview(iter(['1', '2'])) == ['1'], 'AB': deliver([1, 2]) == ['1', '2']}\nprint(json.dumps({'checks': c, 'errors': []}))\nraise SystemExit(0 if all(c.values()) else 1)\n")
        task = {"requirements": ["A", "B", "AB"], "grader_argv": [sys.executable, str(root / "checks.py")], "grader_files": {}}
        result = grade(task, root, root / "grade.json")
        assert result["valid"] and result["checks"] == {"A": True, "B": True, "AB": False}
        # A crashed grader must never satisfy an expected-negative control.
        task["grader_argv"] = [sys.executable, "-c", "raise ImportError('missing')"]
        assert not grade(task, root, root / "crash.json")["valid"]
        assert not change_risk({"allowed_paths": ["src"], "preserved_paths": ["notes"]},
                               {"notes/draft": {"sha256": "a"}}, {"notes/draft": {"sha256": "b"}})["pass"]
    print("PASS: individual slices pass, composed result rejected, grader crash rejected, dirty mutation rejected")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("audit")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--tasks-only", action="store_true", help="Audit private task packs before workflows/routes are frozen")
    p.set_defaults(func=audit)
    p = commands.add_parser("prepare")
    for flag in ("manifest", "audit", "review", "output"):
        p.add_argument("--" + flag, type=Path, required=True)
    p.set_defaults(func=prepare)
    p = commands.add_parser("run")
    p.add_argument("--pilot", type=Path, required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--retry-reason")
    p.add_argument("--timeout", type=float)
    p.set_defaults(func=run_one)
    p = commands.add_parser("accept-review")
    p.add_argument("--pilot", type=Path, required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--review", type=Path, required=True)
    p.set_defaults(func=accept_review)
    p = commands.add_parser("report")
    p.add_argument("--pilot", type=Path, required=True)
    p.set_defaults(func=report)
    p = commands.add_parser("selftest")
    p.set_defaults(func=selftest)
    args = parser.parse_args()
    try:
        if hasattr(args, "pilot"):
            with state_lock(args.pilot):
                passed = args.func(args)
        else:
            passed = args.func(args)
    except (ValueError, KeyError, OSError, StopIteration) as exc:
        parser.exit(2, str(exc) + "\n")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
