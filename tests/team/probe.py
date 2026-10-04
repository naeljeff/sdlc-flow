#!/usr/bin/env python3
"""Fresh native CLI sessions. Python stdlib; private artifacts, no token ceilings."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def inventory(root):
    """Hash content and executable bits; do not follow links or ignore dirty files."""
    root = Path(root).resolve()
    found = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "__pycache__"))
        for name in sorted(files + [d for d in dirs if (Path(directory) / d).is_symlink()]):
            path = Path(directory) / name
            if path.suffix == ".pyc":
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                found[relative] = {"symlink": os.readlink(path)}
            else:
                found[relative] = {"sha256": digest(path.read_bytes()),
                                   "executable": bool(path.stat().st_mode & 0o111)}
    return found


def tree_digest(root):
    return digest(json.dumps(inventory(root), sort_keys=True).encode())


def inside(path, root):
    return Path(path).resolve().is_relative_to(Path(root).resolve())


def private_directory(path, workspace):
    path = Path(path).resolve()
    if inside(path, workspace) or inside(workspace, path):
        raise ValueError("Private artifacts and subject workspace must be disjoint")
    if any((parent / ".git").exists() for parent in (path, *path.parents)):
        raise ValueError("Private artifacts must be outside every Git checkout")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def native_argv(backend, workspace, model=None, effort=None, concurrency=None, allowed_directories=(), allowed_tools=()):
    if backend == "codex":
        argv = ["codex", "exec", "--json", "--color", "never", "--sandbox",
                "workspace-write", "--enable", "multi_agent", "--skip-git-repo-check", "--cd", str(workspace)]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["--config", "model_reasoning_effort=" + json.dumps(effort)]
        if concurrency is not None:
            argv += ["--config", "agents.max_threads=" + str(concurrency)]
        for directory in allowed_directories:
            argv += ["--add-dir", str(Path(directory).resolve())]
        return argv + ["-"]
    if backend == "claude":
        argv = ["claude", "--print", "--verbose", "--output-format", "stream-json",
                "--forward-subagent-text",
                "--permission-mode", "acceptEdits", "--permission-prompts", "none",
                "--session-id", str(uuid.uuid4())]
        if allowed_tools:
            approved = {"Bash(python3 overlap.py a)", "Bash(python3 overlap.py b)"}
            if not set(allowed_tools) <= approved:
                raise ValueError("This probe supports only the reviewed inert overlap-command allowlist")
            argv += ["--allowedTools", *allowed_tools]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["--effort", effort]
        for directory in allowed_directories:
            argv += ["--add-dir", str(Path(directory).resolve())]
        return argv
    raise ValueError("Backend must be codex or claude")


def metadata(events, backend):
    models, sessions, usage_blocks, errors, native_calls = set(), set(), [], [], []
    root_models, worker_models = set(), {}
    completed = False
    cost = None
    for event in events:
        kind = event.get("type")
        if backend == "codex":
            if kind == "thread.started" and event.get("thread_id"):
                sessions.add(event["thread_id"])
            if kind == "turn.completed":
                completed = True
                usage_blocks.append(event.get("usage", {}))
            if kind in ("error", "turn.failed"):
                errors.append(event)
            # Only structured host fields count; never parse assistant prose.
            if kind in ("session_meta", "session.started", "turn.started") and isinstance(event.get("model"), str):
                models.add(event["model"])
                root_models.add(event["model"])
            item = event.get("item", {})
            if item.get("type") in ("collab_tool_call", "collab_agent_tool_call"):
                native_calls.append(item)
        else:
            if kind == "system" and event.get("subtype") == "init":
                if event.get("session_id"):
                    sessions.add(event["session_id"])
                if event.get("model"):
                    models.add(event["model"])
                    root_models.add(event["model"])
            if kind == "assistant" and isinstance(event.get("message"), dict):
                message = event["message"]
                if message.get("model"):
                    models.add(message["model"])
                    parent = event.get("parent_tool_use_id")
                    if parent:
                        worker_models.setdefault(parent, set()).add(message["model"])
                    else:
                        root_models.add(message["model"])
                for block in message.get("content", []):
                    if block.get("type") == "tool_use" and block.get("name") in ("Agent", "Task"):
                        native_calls.append(block)
            if kind == "result":
                completed = not event.get("is_error", False) and event.get("subtype") == "success"
                usage_blocks.append(event.get("usage", {}))
                cost = event.get("total_cost_usd")
                if isinstance(event.get("modelUsage"), dict):
                    models.update(event["modelUsage"])
                if not completed:
                    errors.append(event)
    fields = {"input_tokens": "input_tokens", "output_tokens": "output_tokens",
              "cached_input_tokens": "cached_input_tokens" if backend == "codex" else "cache_read_input_tokens",
              "cache_creation_input_tokens": "cache_creation_input_tokens"}
    usage = {name: sum(block[key] for block in usage_blocks)
             if usage_blocks and all(isinstance(block.get(key), int) and not isinstance(block[key], bool)
                                     and block[key] >= 0 for block in usage_blocks) else None
             for name, key in fields.items()}
    return {"reported_models": sorted(models) or None, "session_ids": sorted(sessions),
            "root_reported_models": sorted(root_models) or None,
            "worker_reported_models": {key: sorted(value) for key, value in worker_models.items()},
            "reported_usage": usage, "reported_cost_usd": cost,
            "usage_scope": "CLI receipt; descendant coverage unverified",
            "full_workflow_usage": None, "full_workflow_cost_usd": None,
            "native_delegation_calls": native_calls, "host_completed": completed,
            "host_errors": errors}


def route_compliance(receipt, requested_model, expected_root_models=None):
    expected = expected_root_models or ([requested_model] if requested_model else [])
    observed = receipt.get("root_reported_models") or []
    if not expected or not observed:
        return {"status": "unknown", "pass": False, "expected": expected, "observed": observed}
    matched = set(observed) <= set(expected)
    return {"status": "matched" if matched else "mismatch", "pass": matched,
            "expected": expected, "observed": observed}


def codex_session_models(session_ids):
    """Read only host turn metadata in this invocation's exact session files."""
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
    models, evidence = set(), []
    for session_id in session_ids:
        try:
            uuid.UUID(session_id)
        except (ValueError, TypeError):
            continue
        for path in home.glob(f"**/*{session_id}.jsonl"):
            for line in path.open(errors="replace"):
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "turn_context":
                    model = event.get("payload", {}).get("model")
                    if isinstance(model, str):
                        models.add(model)
                        evidence.append({"session_id": session_id, "model": model,
                                         "source": "local host turn_context"})
    return sorted(models), evidence


def codex_descendants(session_ids):
    """Follow only exact native parent edges; never inspect unrelated conversations."""
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    results = []
    databases = sorted(home.glob("state_*.sqlite"))
    if not databases:
        return results
    # Host-version-specific optional metadata; absence is unknown, never inferred.
    try:
        connection = sqlite3.connect(databases[-1].as_uri() + "?mode=ro", uri=True)
        pending, seen = list(session_ids), set(session_ids)
        while pending:
            parent = pending.pop()
            requests = {}
            for path in (home / "sessions").glob(f"**/*{parent}.jsonl"):
                for line in path.open(errors="replace"):
                    try:
                        event = json.loads(line)
                        item = event.get("payload", {})
                        if event.get("type") == "response_item" and item.get("name") == "spawn_agent":
                            arguments = json.loads(item.get("arguments", "{}"))
                            requests[arguments.get("task_name")] = arguments.get("model")
                    except (ValueError, TypeError):
                        continue
            rows = connection.execute(
                "SELECT t.id,t.model,t.agent_path,e.status FROM thread_spawn_edges e "
                "JOIN threads t ON t.id=e.child_thread_id WHERE e.parent_thread_id=?", (parent,)).fetchall()
            for child, configured, agent_path, status in rows:
                if child in seen:
                    continue
                uuid.UUID(child)
                seen.add(child)
                models, evidence = codex_session_models([child])
                results.append({"parent_session_id": parent, "session_id": child,
                                "agent_path": agent_path, "host_edge_status": status,
                                "requested_model": requests.get((agent_path or "").rsplit("/", 1)[-1]),
                                "host_configured_model": configured,
                                "reported_models": models or None, "model_evidence": evidence})
                pending.append(child)
        connection.close()
    except (sqlite3.Error, OSError, ValueError):
        return []
    return results


def run_session(workspace, output, prompt, backend, model=None, effort=None,
                concurrency=None, timeout=None, allowed_directories=(), expected_root_models=None, allowed_tools=()):
    workspace = Path(workspace).resolve()
    output = Path(output).resolve()
    private_directory(output.parent, workspace)
    for directory in allowed_directories:
        if inside(output, directory) or inside(directory, output) or inside(output.parent, directory):
            raise ValueError("Writable worker grants must not overlap private receipts")
    output.mkdir(mode=0o700)  # A retry is a new directory, never overwritten.
    argv = native_argv(backend, workspace, model, effort, concurrency, allowed_directories, allowed_tools)
    (output / "prompt.txt").write_text(prompt)
    initial = inventory(workspace)
    started_utc = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    receipt = {"schema": 1, "backend": backend, "argv": argv, "fresh_session": True,
               "requested_model": model, "requested_effort": effort,
               "requested_concurrency": concurrency, "workspace": str(workspace),
               "expected_root_models": expected_root_models,
               "allowed_directories": [str(Path(p).resolve()) for p in allowed_directories],
               "prompt_sha256": digest(prompt.encode()), "started_utc": started_utc,
               "status": "running", "initial_inventory": initial}
    write_json(output / "receipt.json", receipt)
    observed = []
    timed_out = interrupted = False
    returncode = None
    process = None
    try:
        with (output / "stdout.jsonl").open("wb") as stdout, (output / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(argv, cwd=workspace, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=stderr, start_new_session=True)
            receipt["process_pid"] = process.pid
            write_json(output / "receipt.json", receipt)

            def drain():
                for line in iter(process.stdout.readline, b""):
                    stdout.write(line)
                    stdout.flush()
                    observed.append({"elapsed_seconds": time.monotonic() - started,
                                     "line_sha256": digest(line)})

            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            try:
                process.stdin.write(prompt.encode())
                process.stdin.close()
                returncode = process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                timed_out = isinstance(exc, subprocess.TimeoutExpired)
                interrupted = not timed_out
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    returncode = process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    returncode = process.wait()
            finally:
                reader.join(timeout=10)
    except (OSError, BrokenPipeError) as exc:
        receipt["launch_error"] = str(exc)
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    raw_events, malformed = [], 0
    for line in (output / "stdout.jsonl").read_text(errors="replace").splitlines() if (output / "stdout.jsonl").exists() else []:
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                raw_events.append(event)
            else:
                malformed += 1
        except ValueError:
            malformed += 1
    receipt.update(metadata(raw_events, backend))
    if backend == "codex":
        models, evidence = codex_session_models(receipt["session_ids"])
        receipt["reported_models"] = sorted(set(receipt["reported_models"] or []) | set(models)) or None
        receipt["root_reported_models"] = sorted(set(receipt["root_reported_models"] or []) | set(models)) or None
        receipt["model_evidence"] = evidence
        receipt["native_descendants"] = codex_descendants(receipt["session_ids"])
    receipt["model_identity_scope"] = "host-reported route; upstream provider identity is not attested"
    receipt.update({"returncode": returncode, "timed_out": timed_out, "interrupted": interrupted,
                    "duration_seconds": time.monotonic() - started,
                    "ended_utc": datetime.now(timezone.utc).isoformat(),
                    "final_inventory": inventory(workspace), "malformed_event_lines": malformed,
                    "timing_scope": "root process including synchronous retries/subagents; detached workers unverified",
                    "full_workflow_timing_complete": False})
    receipt["route_compliance"] = route_compliance(receipt, model, expected_root_models)
    receipt["transport_completed"] = returncode == 0 and receipt["host_completed"] and not receipt["host_errors"]
    receipt["status"] = "completed" if receipt["transport_completed"] and receipt["route_compliance"]["pass"] else "failed"
    write_json(output / "observations.json", observed)
    write_json(output / "receipt.json", receipt)
    return receipt


def prepare_delegation(args):
    """Create a bounded shared-packet workload, never claim native proof from it alone."""
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    if any(workspace.iterdir()):
        raise ValueError("Delegation probe requires an empty disposable workspace")
    if args.models[0] == args.models[1]:
        raise ValueError("Heterogeneous probe needs two distinct requested models")
    packet = {"schema": 1, "task": "native-overlap", "requirements_revision": 1,
              "requirements": ["Read this shared packet", "Preserve unrelated-draft.txt exactly",
                               "Use only native delegation", "Return scoped worker evidence"],
              "workers": {name: {"requested_model": model, "owned_paths": [name + ".ready", name + ".json"]}
                          for name, model in zip(("a", "b"), args.models)}}
    write_json(workspace / "packet.json", packet)
    (workspace / "unrelated-draft.txt").write_text("Keep this user's unfinished draft.  \n")
    (workspace / "overlap.py").write_text('''import hashlib, json, os, pathlib, sys, time
root = pathlib.Path(__file__).resolve().parent
name = sys.argv[1]
assert name in ("a", "b")
peer = "b" if name == "a" else "a"
packet = (root / "packet.json").read_bytes()
spec = json.loads(packet)
assert name in spec["workers"] and spec["requirements_revision"] == 1
started = time.time()
with (root / (name + ".ready")).open("x") as handle:
    handle.write(str(os.getpid()))
deadline = time.monotonic() + 90
while not (root / (peer + ".ready")).exists():
    if time.monotonic() > deadline:
        raise RuntimeError("Peer did not overlap; sequential launch cannot pass")
    time.sleep(0.05)
time.sleep(1)
result = {"worker": name, "pid": os.getpid(), "started": started,
          "ended": time.time(), "packet_sha256": hashlib.sha256(packet).hexdigest(),
          "requirements_revision": 1}
with (root / (name + ".json")).open("x") as handle:
    json.dump(result, handle)
print(json.dumps(result))
''')
    prompt = ("Run a native delegation compatibility experiment. You are the orchestrator. "
              "Read packet.json. Use your host's native spawn/Agent tool to start TWO fresh workers "
              "before waiting for either, with these requested models: " + json.dumps(packet["workers"])
              + ". Do not use subprocess model CLIs, nested worker delegation, or silently substitute models. "
              "Give each worker packet.json and its ownership. Worker a must read the packet and run "
              "`python3 overlap.py a`; worker b must read it and run `python3 overlap.py b`. "
              "Workers must report the tool result and preserve unrelated-draft.txt. "
              "Wait for both, inspect both result files, verify packet identity and overlapping intervals, "
              "and report actual native model-selection limitations. Never invent host metadata. "
              "Do not launch replacement workers after a failed capability; report the failure. "
              "Do not commit or change global settings.\n")
    args.prompt.write_text(prompt)
    print(json.dumps({"workspace": str(workspace), "prompt": str(args.prompt),
                      "classification": "prepared native experiment; not yet verified"}))


def delegation_main():
    parser = argparse.ArgumentParser(description="Prepare separate native heterogeneous experiment")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--models", nargs=2, required=True)
    args = parser.parse_args(sys.argv[2:])
    prepare_delegation(args)


def main():
    if sys.argv[1:2] == ["prepare-delegation"]:
        delegation_main()
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--backend", choices=("codex", "claude"), required=True)
    parser.add_argument("--model")
    parser.add_argument("--expected-root-model", action="append", default=[], help="Reviewed expected host-reported route identity")
    parser.add_argument("--effort")
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--add-dir", type=Path, action="append", default=[], help="Explicit isolated worker workspace root")
    parser.add_argument("--allow-tool", action="append", default=[], help="Reviewed exact inert overlap command only")
    parser.add_argument("--timeout", type=float, help="Operational seconds; an interrupted run is not a completion")
    args = parser.parse_args()
    if args.concurrency is not None and args.concurrency < 1:
        parser.error("concurrency must be positive")
    result = run_session(args.workspace, args.output, args.prompt.read_text(), args.backend,
                         args.model, args.effort, args.concurrency, args.timeout, args.add_dir, args.expected_root_model,
                         args.allow_tool)
    print(json.dumps({key: result[key] for key in ("status", "reported_models", "reported_usage", "duration_seconds")}))
    raise SystemExit(0 if result["status"] == "completed" else 1)


if __name__ == "__main__":
    main()
