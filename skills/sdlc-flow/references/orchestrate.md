# One orchestrator, bounded workers

Use the [assignment](../assets/assignment.json) and [result](../assets/worker-result.json) contracts. The optional [record helper](team-helper.md) validates task consistency through [team.py](../scripts/team.py); it does not launch agents or prove software correctness.

Use Team mode for independent substantial slices or when the user requests parallel agents. Use native agent tools when the host provides them. Read [host-adapters.md](host-adapters.md) before selecting routes. A sequential task stays with one agent.

## Shape the board

Resolve the effective request, latest clarifications, project rules, starting source, pre-existing changes, and observable acceptance. Give each required outcome an ID. Include behavior to preserve and prohibited effects. Record path limits from the request and project rules as brief constraints (permitted paths; paths that must stay unchanged). Without explicit limits, permit only the paths the outcome requires. Owned paths and the final diff stay inside them. Record assumptions requiring a probe. Check the actual contracts and callers before choosing file boundaries.

Break work into runnable feature slices with dependencies. Resolve common interfaces first; assign one owner to shared schemas, lockfiles, routes, or design tokens. Prefer end-to-end feature ownership. Useful independent research or tests may run while a contract owner works. Separate contexts do not make dependent code independent.

The board distinguishes pending, ready, running, review, integrated, verified, blocked, and obsolete. Integrated means applied to the task's candidate and recorded on the board; it does not imply a Git commit or publication. Record owner, role/model, workspace, generation, requirements revision, dependencies, acceptance IDs, and evidence per assignment.

## Dispatch

The orchestrator owns canonical task state and accepted memory. Give every worker a bounded assignment: outcome, current constraints, relevant acceptance IDs, dependencies, source snapshot, owned paths, workspace, checks, shared-memory revision, result destination, and next action. Use the packaged contracts; the same fields can be maintained through host file tools when the optional helper is unavailable.

Workers read shared facts before acting on an interface and before returning a result. They submit sourced discoveries in their own inbox; they do not rewrite shared decisions or launch untracked agents. If a contract or ownership must change, return a request to the orchestrator. Checkpoint partial work before a handoff. See [shared-memory.md](shared-memory.md).

Fill available slots with independent ready work, prioritizing the critical path. Reuse slots for follow-ups. While workers run, integrate finished slices, resolve decisions, or run useful checks. Do not duplicate their exploration. Add agents only when there is independent work and enough integration capacity.

## Isolate writers

Parallel code writers use separate Git worktrees or verified isolated copies. A shared checkout may host read-only workers. Worktrees do not isolate ports, fixture databases, or output directories; allocate those separately. Give each role a fresh unique scratch directory (for example `mktemp -d` under the task directory or the host temp directory) and pass its path in the worker prompt; each role deletes only that directory.

Start each writer from a declared task snapshot. Account for authorized dirty source and task-relevant untracked files. Preserve unrelated changes; a clean worktree does not automatically contain the user's uncommitted code. Record the overlay used to create the task snapshot without resetting or implicitly stashing the user's checkout.

Each worker returns complete/partial/blocked/failed status, actual changed paths, patch baseline, checks with source identities, limitations, proposed memory updates, observable model metadata, and exact next action. Do not accept a status sentence as verification.

When the helper context supplies `result_destination`, use that exact task-owned path for the worker's durable result JSON. Keep source edits in the isolated writer copy. Do not invent a parallel result filename: after a reset, the next orchestrator must find the same result without replaying the worker conversation. After confirming the exact native task has terminated, validate the result's assignment, generation, requirements revision, snapshot, manifest and checks, then ingest that same path with `--worker-ended` before checkpointing or resetting. Ingestion records the immutable result in canonical task state and moves a complete or partial result to `review`; it does not integrate the patch or pass the final acceptance gate. If the file already exists at `result_destination`, ingestion verifies it matches before indexing it. A fresh root can recover the indexed review result and continue integration.

Result contents, file existence, and a worker-authored `worker_ended` field do not prove that the host task terminated. Check the native host's terminal status for the exact assignment and generation, and record task/session identity and status evidence separately from the worker result. Compare the returned result payload with the durable JSON when the host exposes one; retain the file hash and native result observation. If the host confirms termination but the result is not yet available, use `transition --to running --evidence <termination.json>` to record that the worker ended while preserving the result as pending; ingest it when it becomes available. If a result must deliberately remain un-ingested across a checkpoint/reset, record termination with the same-state transition first, then ingest the exact path on resume. The helper preserves this recorded `live: false` status when the later result is ingested. Missing model or usage telemetry remains `unknown` but does not keep a worker marked live after its exact terminal status is established. If assignment identity or terminal status is unknown, preserve live ownership until it can be verified.

## Integrate and verify

Check generation, effective requirements, dependency state, patch baseline, owned paths, and evidence before accepting a result. Apply each valid result in dependency order to one integration workspace so only its changes against the recorded baseline land: apply a diff, or copy a whole file only when the integration copy still matches that baseline; stop on any mismatch or conflict. With the helper, run `transition --to integrated` with the applied manifest right after applying each result and before any checkpoint; a result is integrated only when that command succeeds, and applied source whose assignment is still `review` is reported as not integrated. Resolve conflicts through one owner and recheck affected contracts. Patch applicability proves syntax of application, not compatibility of behavior.

Run checks on the integrated product that reach each required user/API outcome, execute changed documentation examples, preserve adjacent supported behavior, and exercise meaningful error/state transitions. Two passing worker suites may still conceal an integration defect. Use [review.md](review.md) for a fresh independent review of the combined candidate in Team mode. Renew affected checks and review evidence after fixes.

Completion follows the Team criteria in SKILL.md Finish, with no unresolved blocking finding, unrelated work preserved, and unavailable runtime proof recorded. Report the first runnable slice and the final verified result separately. Publication follows the user's authorization and project rules.

## Recover

Persist changes in requirements, consequential facts, accepted results, integrated slices, failures, and handoffs. After a context reset, read the task record, inspect current source, and check live workers before dispatching replacements. Never reclaim a live worker because time elapsed. Resume partial work or issue a new generation only after establishing the former owner has stopped.

User corrections invalidate affected assignments and evidence. Notify affected workers with the new requirements revision; retain unaffected work after checking it against the effective request. Respect provider backoff, user pause/cancel, and real blockers. Repeated identical failure on unchanged inputs calls for diagnosis or a changed strategy, not another unchanged retry.
