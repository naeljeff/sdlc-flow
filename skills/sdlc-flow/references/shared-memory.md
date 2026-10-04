# Common task knowledge

All agents use one accepted knowledge source at a known revision. Shared files are external memory, not a shared model context window. The orchestrator alone updates canonical requirements, facts, decisions, and assignment state. Workers publish proposed updates in separate task-owned inboxes; the orchestrator verifies their sources, resolves conflicts, and makes accepted updates available to affected workers.

Create a task-local directory under `.sdlc-flow/tasks/<id>/` for Team mode. Keep the effective brief, dependency board, accepted facts, assignment contracts, inboxes, evidence, and checkpoints there. Do not overwrite another task or use a shared active-task pointer. A compact readable status view should expose owners, blocked work, integrated outcomes, evidence, and one exact next action. It is a view of canonical records, not a competing authority.

## What to keep

Every fact or decision needs an ID, scope, source reference, relevant source identity, confidence/status, and its practical implication. Hypotheses stay provisional. A source change makes affected facts stale until rechecked. Supersede a disproved claim instead of appending a contradiction. A worker's confident prose does not make a fact verified.

The effective brief preserves the user's outcome, acceptance IDs, constraints, and latest corrections. Reconcile changes with applicable project instructions and authoritative contracts. Memory notes preserve intent and prior decisions; current source and observed behavior establish implementation facts. Task knowledge does not grant permission to edit global/personal memory or publish private evidence.

## Context packets

Give each worker current requirements relevant to its outcome, all mandatory shared constraints, interface decisions, acceptance IDs, workspace/source identity, task-memory revision, decisive evidence, and exact next action. Include a path/index for targeted retrieval. Keep logs and screenshots in evidence files and record what they showed, including route/state and source provenance.

Do not send the entire conversation to every worker. Send relevant updates after a new decision or correction. Workers refresh before crossing a changed interface or finishing. If mandatory context does not fit, narrow/split the assignment or handle its larger context explicitly; never silently truncate requirements.

If a worker cannot read the central directory within its permitted filesystem, supply a versioned read-only packet and collect findings through an allowed host channel. Do not bypass its sandbox with symlinks or broaden permissions merely to share knowledge.

## Checkpoints and resumption

Persist requirements/memory revisions, source identities, active agent IDs, assignment generations and owners, accepted results, failures, evidence limitations, next ready work, and one exact next action. Checkpoint after consequential decisions, verified integrations, requirements changes, failures, and before handoff or likely context reset.

On resume, inspect source and existing diffs, revalidate claims affected by changes, and establish live worker ownership. A missing chat transcript is not evidence a worker stopped. Avoid duplicate dispatch. Keep task-level cost/time accounting across replacement sessions; missing usage is unknown, not zero. Resume from decisions and current code, without replaying every tool call.

Use the optional bundled helper for record validation when available. Host file tools can implement the same single-writer protocol; they do not supply helper-enforced consistency checks. Neither protocol nor helper proves semantic software correctness.
