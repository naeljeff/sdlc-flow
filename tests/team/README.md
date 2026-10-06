# Native team evaluation

These Python 3 runners use only the standard library and installed native CLIs.
Run them from the repository root. On the supported macOS/Linux host, advisory
file locks serialize evaluator state writes. They do not install software, edit
CLI configuration, or read credentials. Model prompts go through stdin and all
commands use argument lists, never shell interpolation.

Keep task manifests, graders, reference controls, subject workspaces, transcripts,
and receipts in a private directory **outside this repository**. Do not commit
those files. Private outcome files must also be outside each subject checkout.
This is logical separation, not an OS sandbox preventing a model from reading
all sibling paths: review access traces and discard contaminated attempts.

## Mechanical smoke

```sh
python3 tests/team/evaluate.py selftest
python3 -m py_compile tests/team/probe.py tests/team/evaluate.py tests/team/recovery.py
```

The self-test demonstrates two individually passing slices whose composition
fails, a grader crash, and an unrelated dirty-file mutation. It is a mechanical
test, not an evaluated model attempt or native recovery evidence.

## Fresh native session

```sh
python3 tests/team/probe.py --backend codex \
  --workspace /private/subject --output /private/receipts/attempt-1 \
  --prompt /private/prompts/task.txt --model MODEL --effort EFFORT --concurrency 3
```

For Claude, select `--backend claude` and only a model/effort supported by that
installation. A new session ID is requested for every invocation. Codex uses
fresh `exec`, JSON events, workspace-write sandbox, and native multi-agent mode.
Claude uses print/stream-json with `bypassPermissions`, because `acceptEdits`
without prompts denies compound shell commands. Its seatbelt sandbox stays on by
default and cannot be escaped. Claude subjects get an allow-listed environment
(no inherited auth, effort, proxy or model overrides; auto-memory off; subagent
model pinned to the route model), no MCP servers, and no Workflow, artifact,
web, cron or remote-trigger tools. Run them in a disposable directory outside
any folder with an ancestor `CLAUDE.md` or `AGENTS.md`.

The sandbox hides other processes from `ps`, which live-worker recovery must
observe. Only for that, opt in with `--claude-unsandboxed` (probe CLI) or
`"claude_unsandboxed": true` in the reviewed route. The subject's shell and file
tools can then reach anything your account can, so use a disposable machine or
account, launch the runner from an unsandboxed shell, and compare protected
paths before and after the run. They are distinct backends; do not compare them
as a matched workflow experiment.

An optional `--timeout SECONDS` is an operational interruption, never a token
budget or successful completion. Retries get new immutable directories; retain
every receipt. `stdout.jsonl`, `stderr.log`, `prompt.txt`, observation timestamps,
and `receipt.json` persist privately even after failure. Reported model fields
come from structured host events. For Codex, only the new session ID's local
`turn_context` records are read when available. These identify the host route,
not a cryptographic attestation of the upstream provider. Self-reported model
names in prose are ignored.

Missing usage, cost, identity, and descendant coverage remain `null`. Root CLI
duration includes synchronous retries and workers, but detached work and review
coverage require separate receipts. Never treat a missing receipt as zero.

## Separate heterogeneous overlap experiment

```sh
python3 tests/team/probe.py prepare-delegation \
  --workspace /private/native-subject --prompt /private/prompts/overlap.txt \
  --models FIRST_VERIFIED_ROUTE SECOND_VERIFIED_ROUTE
python3 tests/team/probe.py --backend codex \
  --workspace /private/native-subject --output /private/receipts/overlap-1 \
  --prompt /private/prompts/overlap.txt --model ORCHESTRATOR_ROUTE --concurrency 3
```

The packet assigns two native workers separate output files, a shared revision,
and a preserved draft. Their tool processes rendezvous and emit timed results.
Passing requires **all** of: host-native delegation events, two distinct
host-reported worker identities, two overlapping result intervals, matching
packet hashes, preserved dirty bytes, and no silent model fallback. File
timestamps alone prove only overlapping tool processes; they do not prove model
identity or native delegation. Repeat separately per supported host. An
unavailable second model leaves that host's heterogeneous gate unverified.

## Controlled eight-attempt pilot

The private manifest has `schema: 1`, exactly two `tasks`, `candidate` and `dev`
arms, one shared `route`, and an approved shared `compatibility` adaptation.
Each arm specifies a skill directory and `sha256` from `probe.tree_digest`.
The route freezes `backend`, root `model`, `effort`, `concurrency`,
`worker_models`, and `tools_contract`. Compatibility freezes a neutral
instruction, dependency alias map, and copied support-skill hashes. Both arms
receive the same dependency copies and adaptation.

Each task supplies these fields:

| Field | Meaning |
| --- | --- |
| `id`, `brief` | Opaque task ID and complete effective user requirements |
| `source`, `source_sha256` | Frozen real-source snapshot including dirty overlay |
| `provenance` | Public upstream URL, exact Git revision, local clone path |
| `requirements` | IDs checked automatically |
| `review_requirements` | Additional IDs requiring independent qualitative review |
| `allowed_paths`, `preserved_paths` | Scope prefixes and protected dirty/support files |
| `grader_argv`, `grader_files` | Private argv with `{python}`/`{workspace}`, all grader file hashes |
| `baseline_failures` | Exact required outcomes the unchanged source must fail |
| `controls` | Positive and targeted negative source trees, hashes, exact expected booleans |

A grader prints exactly `{"checks":{"ID":true},"errors":[]}`. Exit 0 means
every check passed; exit 1 means a valid expected product failure. Any other
exit, missing/extra IDs, invalid JSON, exception, or nonempty `errors` is a
harness failure and cannot establish a negative control. The assessment author
must distinguish declared missing capabilities from unexpected runtime errors.

```sh
python3 tests/team/evaluate.py audit --tasks-only \
  --manifest /private/task-packs.json --output /private/task-audit
# Freeze arms, route and shared adaptations into /private/manifest.json.
python3 tests/team/evaluate.py audit \
  --manifest /private/manifest.json --output /private/final-audit
python3 tests/team/evaluate.py prepare \
  --manifest /private/manifest.json --audit /private/final-audit/audit.json \
  --review /private/independent-preflight.json --output /private/pilot
python3 tests/team/evaluate.py run --pilot /private/pilot/pilot.json --run TASK-1-candidate
python3 tests/team/evaluate.py accept-review --pilot /private/pilot/pilot.json \
  --run TASK-1-candidate --review /private/TASK-1-candidate-review.json
python3 tests/team/evaluate.py report --pilot /private/pilot/pilot.json
```

The preflight review records `approved`, `reviewer`, nonempty `findings`, the
canonical sorted-JSON `manifest_sha256`, and `audit_sha256` of the audit bytes.
The eight runs are two tasks × two workflows × two repetitions, with arm order
counterbalanced. Source snapshots, prompts, workflow copies, dependencies, and
private graders are checked for drift. Original upstream Git HEAD is retained;
unrelated dirty files, staging and HEAD changes are checked after the run.
Each run gets a separate sibling `worker-workspaces` directory granted through
the CLI's `--add-dir`. Both prompts name that permitted base and require
non-overlapping writer copies/worktrees outside the integration checkout. Do
not widen the sandbox to the whole private study directory, which contains the
graders and reference controls.

An automatic pass remains `objective_pass: false` until independent review.
The outcome review must have `run`, `reviewer`, `independent_context: true`,
`approved: true`, `manifest_sha256`, the frozen candidate `source_sha256`,
`checks` for every supplemental ID, and nonempty `evidence`. Evidence should
identify meaningful public-API tests actually run, documentation of flags and
defaults, combined outcomes, and unresolved limitations. A subject's claim or
mere existence of test/document files is insufficient. Any review fix needs a
new frozen candidate and fresh affected checks/review; it is rework in the same
run's accounting, not a free new attempt.

No automatic forty-run expansion exists. The report retains the planned 40
workflows and names remaining gates. Objective failure stops expansion; unknown
full-workflow timing/usage cannot support speed or cost claims.

## Ten native fresh-session resets

```sh
python3 tests/team/recovery.py prepare \
  --manifest /private/recovery-manifest.json --output /private/trajectory
python3 tests/team/recovery.py step --state /private/trajectory/recovery.json
# Repeat step for the initial session plus ten fresh resets: eleven sessions.
python3 tests/team/recovery.py report --state /private/trajectory/recovery.json
```

The reviewed manifest contains one source snapshot, persistent workspace, shared
route, brief, allowed/preserved paths, and exactly eleven `phases`. Each phase
has a prompt, external grader fields, and event labels. Required labels are
`checkpointed`, `abrupt`, `requirement_change`, `failed_command`,
`stale_verification`, `dirty_preservation`, `live_worker`, and `completed_worker`.
An abrupt phase requires `interrupt_after_seconds` and an actual interrupted
CLI process. All other phases require completed native sessions. External phase
checks must verify real product progress, requirements, worker process/session
identity, and result consumption. A completed Python state replay cannot pass
as native recovery. Fresh host session IDs must be observable and unique.

The runner never resumes a model conversation: recovery is through current task
files and source. Native compaction is always reported unobserved unless a
separate host-visible experiment demonstrates it. Count usage continuously over
all eleven sessions and their workers; incomplete descendant telemetry remains
unknown.
