#!/usr/bin/env python3
"""Disposable paired-agent benchmark. Python stdlib; Node and Go for their cases."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from cases import BY_ID, CASES, Case


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def tree_digest(root: Path, *, exclude_git: bool = True) -> str:
    entries = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or (exclude_git and ".git" in relative.parts) or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        entries.append([relative.as_posix(), file_digest(path)])
    return digest(json.dumps(entries, separators=(",", ":")).encode())


def run(argv: list[str], cwd: Path, *, timeout: int = 60, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout, env=env)


def git(argv: list[str], cwd: Path) -> str:
    result = run(["git", *argv], cwd)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(argv)}: {result.stderr}")
    return result.stdout.strip()


def write_files(root: Path, files: dict[str, str]) -> None:
    for name, value in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)


def case_selection(name: str) -> list[Case]:
    return [case for case in CASES if name == "full" or case.canary]


def load_manifest(path: Path) -> dict:
    result = json.loads(path.read_text())
    if result.get("schema") != 1:
        raise ValueError("Unsupported benchmark manifest schema")
    return result


def selected_case(manifest: dict, task: str) -> Case:
    if task not in manifest["tasks"] or task not in BY_ID:
        raise ValueError(f"Task {task!r} is not in this benchmark")
    case = BY_ID[task]
    if manifest["tasks"][task]["grader_sha256"] != digest(case.hidden_test.encode()):
        raise ValueError("Grader source changed since prepare; use a new benchmark")
    return case


def candidate_path(manifest: dict, task: str, arm: str) -> Path:
    if arm not in ("old", "new"):
        raise ValueError("arm must be old or new")
    return Path(manifest["tasks"][task]["workspaces"][arm])


def grade_case(case: Case, candidate: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="sdlc-grade-") as temporary:
        isolated = Path(temporary) / "candidate"
        shutil.copytree(candidate, isolated, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        hidden = isolated / case.hidden_filename
        if hidden.exists():
            raise ValueError(f"Candidate may not contain private test filename {case.hidden_filename}")
        hidden.write_text(case.hidden_test)
        if case.stack == "python":
            command = [sys.executable, "-m", "unittest", "-q", hidden.stem]
        elif case.stack == "javascript":
            command = ["node", "--test", case.hidden_filename]
        elif case.stack == "go":
            command = ["go", "test", "./..."]
        else:
            raise ValueError(case.stack)
        env = os.environ.copy()
        env.update({"GOPROXY": "off", "GOSUMDB": "off", "PYTHONDONTWRITEBYTECODE": "1"})
        result = run(command, isolated, timeout=30, env=env)
        return {
            "pass": result.returncode == 0,
            "exit_code": result.returncode,
            "command": command,
            "output": (result.stdout + result.stderr)[-12000:],
            "tree_sha256": tree_digest(candidate),
            "grader_sha256": digest(case.hidden_test.encode()),
        }


def prepare(args: argparse.Namespace) -> None:
    out = args.out.resolve()
    if out.exists():
        raise ValueError(f"Refusing to overwrite {out}")
    if args.old_skill_path.resolve() == args.new_skill_path.resolve():
        raise ValueError("Old and new skill paths must be distinct")
    for skill in (args.old_skill_path, args.new_skill_path):
        if not (skill / "SKILL.md").is_file():
            raise ValueError(f"Missing SKILL.md under {skill}")
    out.mkdir(parents=True)
    manifest = {
        "schema": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "set": args.set,
        "arms": {arm: {"skill_path": str(path.resolve()), "skill_tree_sha256": tree_digest(path.resolve())}
                 for arm, path in (("old", args.old_skill_path), ("new", args.new_skill_path))},
        "tasks": {},
        "protocol": "Both arms start from one fixture commit and identical dirty overlay. Private grader is outside their checkouts.",
    }
    for case in case_selection(args.set):
        task_root = out / case.id
        seed = task_root / "seed"
        seed.mkdir(parents=True)
        write_files(seed, case.files)
        git(["init", "-q", "-b", "main"], seed)
        git(["add", "."], seed)
        git(["-c", "user.name=Benchmark", "-c", "user.email=benchmark@example.invalid", "commit", "-qm", "Seed task"], seed)
        base = git(["rev-parse", "HEAD"], seed)
        workspaces = {}
        for arm in ("old", "new"):
            work = task_root / arm
            git(["clone", "-q", "--no-hardlinks", str(seed), str(work)], task_root)
            write_files(work, {"TASK.md": case.brief})
            write_files(work, case.dirty or {})
            workspaces[arm] = str(work)
        dirty_sha = tree_digest(Path(workspaces["old"]))
        if dirty_sha != tree_digest(Path(workspaces["new"])):
            raise RuntimeError("Starting trees differ")
        manifest["tasks"][case.id] = {
            "stack": case.stack, "family": case.family, "canary": case.canary,
            "base_commit": base, "initial_tree_sha256": dirty_sha,
            "brief_sha256": digest(case.brief.encode()),
            "grader_sha256": digest(case.hidden_test.encode()),
            "workspaces": workspaces,
        }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(out / "manifest.json")


def grade(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.manifest)
    case = selected_case(manifest, args.task)
    candidate = candidate_path(manifest, args.task, args.arm)
    snapshot = args.manifest.parent / "results" / args.task / f"{args.arm}.snapshot"
    source = snapshot if snapshot.is_dir() else candidate
    result = grade_case(case, source)
    result["source"] = "frozen_snapshot" if snapshot.is_dir() else "live_workspace"
    result.update({"task": args.task, "arm": args.arm, "base_commit": manifest["tasks"][args.task]["base_commit"]})
    output = args.manifest.parent / "results" / args.task
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{args.arm}.grade.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("task", "arm", "pass", "exit_code", "tree_sha256")}))
    if not result["pass"]:
        sys.exit(1)


def freeze(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.manifest)
    selected_case(manifest, args.task)
    candidate = candidate_path(manifest, args.task, args.arm)
    base = manifest["tasks"][args.task]["base_commit"]
    if git(["rev-parse", "HEAD"], candidate) != base:
        raise ValueError("Candidate HEAD moved off the shared base; use an uncommitted patch")
    patch = run(["git", "diff", "--binary", "HEAD"], candidate)
    if patch.returncode:
        raise RuntimeError(patch.stderr)
    status = git(["status", "--porcelain=v1", "--untracked-files=all"], candidate)
    result = {"task": args.task, "arm": args.arm, "base_commit": base,
              "initial_tree_sha256": manifest["tasks"][args.task]["initial_tree_sha256"],
              "tree_sha256": tree_digest(candidate), "tracked_patch_sha256": digest(patch.stdout.encode()),
              "status": status.splitlines()}
    output = args.manifest.parent / "results" / args.task
    output.mkdir(parents=True, exist_ok=True)
    snapshot = output / f"{args.arm}.snapshot"
    if snapshot.exists():
        if tree_digest(snapshot) != result["tree_sha256"]:
            raise ValueError("Frozen snapshot exists with different contents; use a new benchmark run")
    else:
        shutil.copytree(candidate, snapshot, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    if tree_digest(snapshot) != result["tree_sha256"]:
        raise RuntimeError("Snapshot differs from candidate; candidate changed during freeze")
    (output / f"{args.arm}.freeze.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / f"{args.arm}.patch").write_text(patch.stdout)
    print(json.dumps({k: result[k] for k in ("task", "arm", "tree_sha256", "tracked_patch_sha256")}))


def record_attempt(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.manifest)
    selected_case(manifest, args.task)
    events = [json.loads(line) for line in args.events.read_text().splitlines() if line.strip()]
    completed = [event for event in events if event.get("type") == "turn.completed"]
    usage_blocks = [event.get("usage", {}) for event in completed]
    needed = ("input_tokens", "output_tokens")
    totals_known = bool(usage_blocks) and all(isinstance(block.get(key), int) for block in usage_blocks for key in needed)
    usage = {key: sum(block.get(key, 0) for block in usage_blocks) for key in ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens")}
    attempt = {"status": args.status, "model": args.model, "reasoning_effort": args.effort,
               "event_trace": str(args.events.resolve()), "event_trace_sha256": file_digest(args.events),
               "usage": usage, "total_tokens": sum(usage[key] for key in needed) if totals_known else None,
               "duration_seconds": args.duration_seconds}
    output = args.manifest.parent / "results" / args.task
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"{args.arm}.attempts.json"
    attempts = json.loads(target.read_text()) if target.exists() else []
    if any(entry["event_trace_sha256"] == attempt["event_trace_sha256"] for entry in attempts):
        raise ValueError("This event trace is already recorded")
    attempts.append(attempt)
    target.write_text(json.dumps(attempts, indent=2) + "\n")
    print(json.dumps({"task": args.task, "arm": args.arm, "attempts": len(attempts), "last_total_tokens": attempt["total_tokens"]}))


def compare(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.manifest)
    for arm in ("old", "new"):
        info = manifest["arms"][arm]
        if tree_digest(Path(info["skill_path"])) != info["skill_tree_sha256"]:
            raise ValueError(f"{arm} skill changed after prepare; use a new benchmark run")
    results = {}
    for task, info in manifest["tasks"].items():
        results[task] = {}
        for arm in ("old", "new"):
            root = args.manifest.parent / "results" / task
            freeze_path, grade_path, attempt_path = [root / f"{arm}.{suffix}.json" for suffix in ("freeze", "grade", "attempts")]
            if not all(path.exists() for path in (freeze_path, grade_path, attempt_path)):
                results[task][arm] = {"complete": False, "reason": "freeze, grade, or attempt receipt missing"}
                continue
            frozen, graded, attempts = (json.loads(path.read_text()) for path in (freeze_path, grade_path, attempt_path))
            if frozen["base_commit"] != info["base_commit"] or graded["base_commit"] != info["base_commit"]:
                raise ValueError(f"Base mismatch for {task}/{arm}")
            snapshot = root / f"{arm}.snapshot"
            if frozen["tree_sha256"] != graded["tree_sha256"] or not snapshot.is_dir() or frozen["tree_sha256"] != tree_digest(snapshot):
                raise ValueError(f"Frozen snapshot and grade differ for {task}/{arm}")
            if graded.get("source") != "frozen_snapshot":
                raise ValueError(f"Grade did not use frozen snapshot for {task}/{arm}")
            totals = [attempt["total_tokens"] for attempt in attempts]
            results[task][arm] = {
                "complete": True, "pass": graded["pass"], "attempts": len(attempts),
                "total_tokens_including_failed_attempts": sum(totals) if totals and all(value is not None for value in totals) else None,
                "grade_exit_code": graded["exit_code"],
                "models": sorted(set(entry["model"] for entry in attempts)),
                "efforts": sorted(set(entry["reasoning_effort"] for entry in attempts)),
            }
        old, new = results[task]["old"], results[task]["new"]
        if old["complete"] and new["complete"] and (old["models"] != new["models"] or old["efforts"] != new["efforts"]):
            raise ValueError(f"Model or effort differs between arms for {task}")
    summary = {}
    for arm in ("old", "new"):
        complete = [pair[arm] for pair in results.values() if pair[arm]["complete"]]
        accepted = [row for row in complete if row["pass"]]
        total_known = len(complete) == len(results) and all(row["total_tokens_including_failed_attempts"] is not None for row in complete)
        token_total = sum(row["total_tokens_including_failed_attempts"] for row in complete) if total_known else None
        summary[arm] = {"tasks_complete": len(complete), "tasks_total": len(results), "accepted": len(accepted),
                        "all_attempt_tokens": token_total,
                        "tokens_per_accepted_solution": token_total / len(accepted) if token_total is not None and accepted else None}
    print(json.dumps({"summary": summary, "tasks": results}, indent=2))


def selftest(args: argparse.Namespace) -> None:
    failures = []
    for case in case_selection(args.set):
        with tempfile.TemporaryDirectory(prefix="sdlc-case-") as temporary:
            root = Path(temporary)
            write_files(root, case.files)
            write_files(root, case.dirty or {})
            empty = grade_case(case, root)
            write_files(root, case.reference)
            reference = grade_case(case, root)
        print(f"{case.id}: unchanged={'PASS' if empty['pass'] else 'FAIL'} reference={'PASS' if reference['pass'] else 'FAIL'}")
        if empty["pass"] or not reference["pass"]:
            failures.append({"task": case.id, "unchanged": empty, "reference": reference})
    if failures:
        print(json.dumps(failures, indent=2))
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("selftest"); p.add_argument("--set", choices=("canary", "full"), default="full"); p.set_defaults(func=selftest)
    p = sub.add_parser("prepare"); p.add_argument("--out", type=Path, required=True); p.add_argument("--set", choices=("canary", "full"), default="canary")
    p.add_argument("--old-skill-path", type=Path, required=True); p.add_argument("--new-skill-path", type=Path, required=True); p.set_defaults(func=prepare)
    for command, func in (("grade", grade), ("freeze", freeze), ("record-attempt", record_attempt)):
        p = sub.add_parser(command); p.add_argument("--manifest", type=Path, required=True); p.add_argument("--task", required=True); p.add_argument("--arm", choices=("old", "new"), required=True); p.set_defaults(func=func)
        if command == "record-attempt":
            p.add_argument("--events", type=Path, required=True); p.add_argument("--status", choices=("completed", "failed", "blocked"), required=True)
            p.add_argument("--model", required=True); p.add_argument("--effort", required=True); p.add_argument("--duration-seconds", type=float)
    p = sub.add_parser("compare"); p.add_argument("--manifest", type=Path, required=True); p.set_defaults(func=compare)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
