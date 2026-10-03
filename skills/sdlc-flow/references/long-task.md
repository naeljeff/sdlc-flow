# Keep long work resumable

Create state only when interruption, multiple sessions, or coordination makes forgotten intent expensive to reconstruct. Use one task-owned directory such as `.sdlc-flow/tasks/<issue-or-date-slug>/STATE.md`; reuse it on continuation. Do not overwrite another task's state or introduce a shared active pointer. If multiple tasks could match “continue,” use current Git changes and recent state to identify the right one; ask only if ambiguity remains.

Copy [working-state.md](../assets/working-state.md) and fill the sections that matter. Keep acceptance and constraints stable; revise them when the user changes the task. For multi-slice or interruptible work, keep one compact row per slice with its status, acceptance evidence, and owner or reviewer when delegated. The single Exact next action in Current position is authoritative. One orchestrator owns the shared state; workers return findings or write separate notes rather than competing to edit it. A plan says what should happen; the state reports what actually happened.

## Checkpoint

Write state after a consequential decision or discovery, a verified slice, a material failure, a requirement change, and before handoff or a likely context reset. Mark a slice verified only when its acceptance evidence is fresh for the changed files; reconcile the row with Git and checks on resume. Record evidence paths and relevant revision or file identity. Do not paste complete command logs, duplicate source files, per-tool activity, or ephemeral reasoning. If the file becomes hard to scan, compress completed work into outcomes while retaining constraints, decision reasons, unresolved risks, and exact next action. Correct stale claims rather than appending a contradictory note.

## Recovery from only “Continue the task”

1. Read the applicable project rules and task state. When the state path is unknown, search the hidden task directory explicitly, for example with `rg --files --hidden .sdlc-flow/tasks`, then identify the goal, acceptance, constraints, current slice, and next action.
2. Inspect Git status, relevant diff, untracked task files, and current files. Separate task changes from pre-existing or unrelated work. Source and observed behavior establish current implementation facts; task state preserves intent and decisions.
3. Revalidate any state claim that could have become stale because code, requirements, or environment changed. Run a cheap relevant check before adding new work when the existing state may be broken.
4. Search and load only files needed for the next slice. Continue with the core work loop, then update the state with fresh evidence.

If the repository is not under Git, use file inspection and available project history instead. State files are task artifacts, not permission to commit or publish them. Coordinate separate agents through bounded ownership and inspect their actual diffs; do not assume a shared checkout is isolated.
