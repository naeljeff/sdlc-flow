# Optional team record helper

Use the actual installed skill path in the examples below. `/installed/sdlc-flow` denotes that directory; it does not require a source checkout. The helper manages records and does not create or run agents.

The helper needs Python 3.9+. POSIX `fcntl` locking has runtime coverage here. The Windows `msvcrt` branch is implemented but requires Windows runtime verification. Git inventory is used when a workspace has a `.git` root; plain isolated copies use a source walk. No provider, network, daemon, installation, personal memory, or global configuration is involved.

## Effective brief

Use JSON, not freeform Markdown:

```json
{
  "outcome": "Deliver the combined product behavior.",
  "acceptance": [{"id": "A1", "text": "Observable acceptance condition."}],
  "constraints": ["Mandatory user or repository constraint."],
  "preserved": ["Existing behavior that must still work."],
  "prohibited": ["Forbidden effect."],
  "interfaces": ["Accepted shared interface decision."]
}
```

The latter four lists default to empty. Acceptance IDs must be unique. `state.json` is the only authority. `BRIEF.json`, `BRIEF.md`, `STATE.md`, `MEMORY.md`, `memory/facts.json` and assignment files are projections, which can be older after an interruption. Read `status` or generate a new `context` from canonical state when recovering.

## CLI sequence

All canonical mutations require the recorded `--owner`. This is a consistency check, not authentication. `--expect-revision N` is optional optimistic concurrency: concurrent commands with one expected revision permit exactly one winner. The local OS lock prevents lost updates even without that flag.

```sh
python3 /installed/sdlc-flow/scripts/team.py init --task /repo/.sdlc-flow/tasks/demo --repo /repo --brief /inputs/brief.json --owner main --owner-agent-id observed-main-id
python3 /installed/sdlc-flow/scripts/team.py add --task /repo/.sdlc-flow/tasks/demo --owner main --input /inputs/assignment.json
python3 /installed/sdlc-flow/scripts/team.py context --task /repo/.sdlc-flow/tasks/demo --assignment feature-a --max-chars 12000
python3 /installed/sdlc-flow/scripts/team.py transition --task /repo/.sdlc-flow/tasks/demo --owner main --assignment feature-a --to running
python3 /installed/sdlc-flow/scripts/team.py transition --task /repo/.sdlc-flow/tasks/demo --owner main --assignment feature-a --to running --evidence /inputs/termination.json
python3 /installed/sdlc-flow/scripts/team.py ingest --task /repo/.sdlc-flow/tasks/demo --owner main --input /inputs/worker-result.json --worker-ended
python3 /installed/sdlc-flow/scripts/team.py transition --task /repo/.sdlc-flow/tasks/demo --owner main --assignment feature-a --to integrated --evidence /inputs/integration.json
python3 /installed/sdlc-flow/scripts/team.py gate --task /repo/.sdlc-flow/tasks/demo --owner main --input /inputs/gate.json
python3 /installed/sdlc-flow/scripts/team.py checkpoint --task /repo/.sdlc-flow/tasks/demo --owner main
python3 /installed/sdlc-flow/scripts/team.py status --task /repo/.sdlc-flow/tasks/demo
```

Create writer workspaces before `add`. They must match the integration snapshot, live outside the integration tree and other active writer trees, and have no shared source hardlinks. The helper does not create, patch, merge, commit, or launch workers. Apply the accepted patch to integration yourself before `transition --to integrated`. The integration input is `{ "manifest": [...] }`, exactly matching the accepted result manifest.

Assignments use the bundled `assets/assignment.json` fields. `add` fills task ID, generation, requirements revision, source snapshot and baseline file identities. Use IDs from the generated context in the result. Paths are normalized relative POSIX paths; `owned_paths` means a file or directory prefix. Ownership conflicts include nested prefixes. `shared_reads` identifies source interfaces that must match current integration at dispatch, result ingestion and integration. Non-owned checked files must also match current integration. The generated context's `result_destination` is the single durable result path for that assignment. A worker or orchestrator may write its result JSON there before ingestion; `ingest --input` verifies an existing JSON artifact matches and indexes that same file. Keep the assignment's source edits in the isolated writer workspace.

A result manifest accounts for **all** changed files relative to the agreed snapshot:

```json
{"path": "src/feature-a.py", "sha256": "current-bytes-sha256", "executable": false}
```

Deletion uses `sha256: null` and `executable: null`. Checks have `command`, `result` (`passed`, `failed`, `unknown`) and optional `checked_files` (`path`, `sha256`). `limitations` and `next_action` are required. Ingestion retains an immutable attempt artifact at `inbox/<agent>/<assignment>-g<generation>.json` and records its hash; later tampering is rejected. Worker `complete`/`partial` only moves to `review`; `blocked`/`failed` moves to `blocked`. Result status alone preserves `live: true`. After the orchestrator observes terminal status for the exact native assignment and generation, ingest its result with `--worker-ended` before checkpointing or resetting; `review` means available for integration, not integrated or verified. If host termination is confirmed before its result is available, use `transition --to running --evidence <termination.json>` to record `live: false` without indexing a result. That evidence must contain `worker_ended: true`, the matching `agent`, and `generation`. A same-state transition can also record termination when a result is intentionally left un-ingested across a recovery boundary; later ingestion of that result preserves `live: false`. Immediate ingestion is the normal path when the result exists. Missing model or usage telemetry stays `unknown` and is independent of whether the host task is still live. There is no worker completion to verified transition.

`transition --to ready` resumes a blocked/review assignment with a new generation; earlier unintegrated edits remain in its baseline comparison. A previously integrated/verified workspace must match current integration when resumed. Dependencies must exist, be acyclic, and reach integrated/verified before dispatch; dependent workspace source must contain the accepted dependency files. `verify --assignment ID --input FILE` is optional scoped verification using the same gate contract for that assignment's acceptance IDs. Final `gate` accepts integrated or verified assignments and needs only one fresh independent review of the combined product.

## Final evidence

`status.source_fingerprint` supplies the current source identity. Gate input covers exactly the effective brief's IDs:

```json
{
  "task_id": "from-status",
  "spec_revision": 1,
  "source_fingerprint": "current-source-fingerprint",
  "acceptance": {
    "A1": [{
      "path": "evidence/outcome.txt",
      "sha256": "evidence-file-sha256",
      "result": "passed",
      "spec_revision": 1,
      "source_fingerprint": "current-source-fingerprint"
    }]
  },
  "review": {
    "independent": true,
    "reviewer": "fresh-reviewer",
    "agent_id": "observed-reviewer-id-or-omit",
    "context_id": "fresh-review-context-id",
    "spec_revision": 1,
    "source_fingerprint": "current-source-fingerprint",
    "evidence": [{
      "path": "evidence/review.txt",
      "sha256": "review-file-sha256",
      "result": "passed",
      "spec_revision": 1,
      "source_fingerprint": "current-source-fingerprint"
    }]
  }
}
```

Files must be nonempty under `task/evidence/`, with no linked or escaping paths. Reviewer identities are compared against known contributor aliases and host-observed `metadata.agent_id` values, plus the optional orchestrator `--owner-agent-id`. All evidence observations must be passed and refer to the current source and requirements. Changed source, altered evidence, omitted acceptance, unknown/failed observations, obsolete requirements or self-review prevent current completion. Matching records cannot prove the truth or semantic adequacy of a check, an independent context or a source claim: the orchestrator must run actual outcome checks and arrange a genuinely independent review.

The fingerprint includes tracked files and relevant non-ignored untracked files; task artifacts, Git internals, `node_modules`, virtual environments and Python bytecode are excluded. Common runtime/cache directories are skipped for plain copies; tracked `dist`/`build` source is included in Git workspaces. Executable mode changes count as source changes. Plain copies should carry only source/configuration and omit generated runtime outputs. Symlink source files/directories require explicit resolution instead of automatic traversal.

## Shared memory, requirement changes and recovery

`memory --input FILE` accepts a JSON list of records:

```json
[{
  "id": "F1",
  "kind": "fact",
  "text": "Verified observation or accepted decision.",
  "confidence": "high",
  "scope": ["src/contracts"],
  "sources": [{"path": "src/contracts/api.py", "sha256": "source-file-sha256"}]
}]
```

Kinds are `fact`, `decision`, `hypothesis`; confidence is `high`, `medium`, `low`, `unknown`. `supersedes` may name an existing record. Source hashes are checked before acceptance. `status` and `context` show stale source facts as stale or omit them; `checkpoint` persists those invalidations. Context includes the complete mandatory brief, assignment and relevant current interface decisions, selected through owned paths and shared reads. Readers with no declared scope can select all current records. Other relevant current facts are optional within the remaining budget. `--max-chars` counts the exact pretty-printed JSON output including its trailing newline. Mandatory content never truncates; an undersized budget fails with guidance to split the assignment or raise the budget.

`revise --brief FILE` replaces effective requirements, increments spec and memory revisions, invalidates current memory and prior verification, and marks assignments obsolete. Running workers retain `live: true` and ownership. Checkpoints preserve live worker identities and never reclaim by elapsed time. After observing a worker has ended, explicitly record:

```sh
python3 /installed/sdlc-flow/scripts/team.py transition --task /repo/.sdlc-flow/tasks/demo --owner main --assignment feature-a --to obsolete --evidence /inputs/ended.json
```

The ended JSON is `{"worker_ended":true,"agent":"worker-a","generation":1}`. A live assignment can similarly receive an ended observation in a same-state transition (for example `--to blocked` or `--to review`), then resume. An accepted partial result retains its immutable attempt; after observing termination, resume as a new generation for the next accepted result. Changed requirements require a new assignment with the new brief, after old live ownership is released.

Metadata fields default to `unknown`: requested model, reported model, effort, backend, agent ID and usage. A known reported model requires `reported_model_source: "host"` or `"provider"`; known usage requires a structured object with `source: "host"` or `"provider"`. Worker prose is not observed upstream identity. The helper records metadata and does not discover or invoke providers.

`status` omits baseline file inventories from assignment projections to keep routine polling compact. Canonical state retains them for validation.
