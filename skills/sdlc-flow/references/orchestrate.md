# One orchestrator, bounded workers

Use Team mode for independent substantial slices or when the user requests parallel agents. Use native agent tools when the host provides them. Read [host-adapters.md](host-adapters.md) before selecting routes. A sequential task stays with one agent.

## Shape the board

Resolve the effective request, latest clarifications, project rules, starting source, pre-existing changes, and observable acceptance. Give each required outcome an ID. Include behavior to preserve and prohibited effects. Record assumptions requiring a probe. Check the actual contracts and callers before choosing file boundaries.

Break work into runnable feature slices with dependencies. Resolve common interfaces first; assign one owner to shared schemas, lockfiles, routes, or design tokens. Prefer end-to-end feature ownership. Useful independent research or tests may run while a contract owner works. Separate contexts do not make dependent code independent.

The board distinguishes pending, ready, running, review, integrated, verified, blocked, and obsolete. Integrated means applied to the task's candidate; it does not imply a Git commit or publication. Record owner, role/model, workspace, generation, requirements revision, dependencies, acceptance IDs, and evidence per assignment.

## Dispatch

The orchestrator owns canonical task state and accepted memory. Give every worker a bounded assignment: outcome, current constraints, relevant acceptance IDs, dependencies, source snapshot, owned paths, workspace, checks, shared-memory revision, result destination, and next action. Use the packaged templates once available; a plain file with these fields also works.

Workers read shared facts before acting on an interface and before returning a result. They submit sourced discoveries in their own inbox; they do not rewrite shared decisions or launch untracked agents. If a contract or ownership must change, return a request to the orchestrator. Checkpoint partial work before a handoff. See [shared-memory.md](shared-memory.md).

Fill available slots with independent ready work, prioritizing the critical path. Reuse slots for follow-ups. While workers run, integrate finished slices, resolve decisions, or run useful checks. Do not duplicate their exploration. Add agents only when there is independent work and enough integration capacity.

## Isolate writers

Parallel code writers use separate Git worktrees or verified isolated copies. A shared checkout may host read-only workers. Worktrees do not isolate ports, fixture databases, or output directories; allocate those separately.

Start each writer from a declared task snapshot. Account for authorized dirty source and task-relevant untracked files. Preserve unrelated changes; a clean worktree does not automatically contain the user's uncommitted code. Record the overlay used to create the task snapshot without resetting or implicitly stashing the user's checkout.

Each worker returns complete/partial/blocked/failed status, actual changed paths, patch baseline, checks with source identities, limitations, proposed memory updates, observable model metadata, and exact next action. Do not accept a status sentence as verification.

## Integrate and verify

Check generation, effective requirements, dependency state, patch baseline, owned paths, and evidence before accepting a result. Apply valid changes in dependency order to one integration workspace. Resolve conflicts through one owner and recheck affected contracts. Patch applicability proves syntax of application, not compatibility of behavior.

Run checks on the integrated product that reach each required user/API outcome, preserve adjacent supported behavior, and exercise meaningful error/state transitions. Two passing worker suites may still conceal an integration defect. Use [review.md](review.md) for a fresh independent review of the combined candidate in Team mode. Renew affected checks and review evidence after fixes.

Completion requires fresh evidence for every current acceptance ID, no unresolved blocking finding, preserved unrelated work, and a clear record of unavailable runtime proof. Report first runnable slice and final verified result separately. Publication follows the user's authorization and project rules.

## Recover

Persist changes in requirements, consequential facts, accepted results, integrated slices, failures, and handoffs. After a context reset, read the task record, inspect current source, and check live workers before dispatching replacements. Never reclaim a live worker because time elapsed. Resume partial work or issue a new generation only after establishing the former owner has stopped.

User corrections invalidate affected assignments and evidence. Notify affected workers with the new requirements revision; retain unaffected work after checking it against the effective request. Respect provider backoff, user pause/cancel, and real blockers. Repeated identical failure on unchanged inputs calls for diagnosis or a changed strategy, not another unchanged retry.
