# Phase 4: Integration and long-session recovery

**Status: implementation updated; end-to-end recovery not demonstrated.** The
frozen eleven-session trajectory stopped at its first gate. The failed result
is retained and reported; it is not counted as a successful recovery.

## Scope

The controlled study was designed to follow one dependent product task through
an initial native Codex root session and ten fresh root sessions. It tests
durable checkpoints, completed and live worker recovery, failed commands, a
process interruption, changed requirements, stale-verification rejection,
dirty-file preservation, and final integrated review. The study concerns
fresh-session recovery; it does not claim native conversation compaction.

The public package includes a reproducible runner at
[`tests/team/recovery.py`](../../tests/team/recovery.py), SHA-256
`b59fbdae06f5c63f3569ea3eca403680be2cea63aa3bf42c87d28663700ebcb7`. The
controlled study used a separate private evaluator runner, SHA-256
`a2e7a0606f9a4eceb15ff3af910d5031f22c82820926bc3bec22f80a70dbf997`. The
private task source, prompts, graders, controls, transcripts, and receipts are
not included in this repository.

## Attempts and evidence

- **v2.4:** An independently approved candidate launched one fresh root
  session. Phase 0 failed `COMPLETED_PENDING`; no reset session ran. Worker
  results were written outside the helper's canonical inbox paths.
- **v2.5:** A prelaunch audit found a stale result path. The candidate was not
  launched.
- **v2.5.1:** An independent exact-hash review approved the corrected frozen
  candidate. One fresh root session ran for 607.1 seconds; the evaluator
  finished in 610.7 seconds including validation. `BOOT` and `DIRTY` passed;
  `COMPLETED_PENDING` failed. No reset session ran.

In v2.5.1, both worker JSON results were saved at the exact `result_destination`
paths returned by the helper, and structured host observations recorded both
native tasks as completed. However, the canonical task ledger still showed both
assignments as `running/live`, with empty result indexes and hashes. The
orchestrator left the results un-ingested across the checkpoint. This is the
strongest explanation supported by the public run artifacts for the failed
gate; the exact predicate is unknown because the evaluator is private.

The path correction therefore fixed result placement but did not finish the
canonical lifecycle transition. A file in the inbox is not an indexed helper
result. The pilot established neither completed-result recovery by a fresh root
nor the ten-reset trajectory.

## General workflow correction

Version `0.3.0-team.3` clarifies the lifecycle in
[`orchestrate.md`](../../skills/sdlc-flow/references/orchestrate.md) and
[`team-helper.md`](../../skills/sdlc-flow/references/team-helper.md): use the
helper-provided result path, verify terminal status for the exact native task
and assignment generation, then ingest the matching result before checkpoint
or reset. Ingestion records the immutable result in `review`; it does not
integrate the patch or satisfy the final acceptance gate. A fresh root can
recover that unintegrated result from canonical state.

If the host confirms termination before a result is available, a same-state
`transition --to running --evidence ...` records `live: false` while preserving
the un-ingested assignment. The helper previously turned `live` back on during
that same-state transition. The fix preserves the terminal state, and a new
regression test covers checkpointing and later ingesting the same result path.
Unknown model or usage telemetry remains unknown; it no longer implies that a
confirmed terminal worker is still live.

The package validator and all 20 team-helper tests pass on the updated source.
The corrected workflow has not yet been run through a newly frozen
eleven-session trajectory. No long-session recovery success, performance
superiority, or full-workflow usage/cost claim is made. Descendant usage and
total token accounting remain unknown.

## Limits

This is useful failure evidence and a tested state-helper correction, not proof
that every host/model combination can recover a long task. The platform must
expose enough native identity and terminal-status evidence to tie a worker to
its assignment. Host status, result content, and canonical task state must be
reported separately. The next controlled run should freeze the updated package
and keep its acceptance criteria unchanged.
