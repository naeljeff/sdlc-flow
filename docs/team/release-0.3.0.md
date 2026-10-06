# SDLC Flow 0.3.0

SDLC Flow 0.3.0 adds an explicit Team mode to the single installable skill: one
orchestrator schedules bounded native workers, keeps one canonical task record and
shared memory, isolates code writers in their own copies, integrates their
results, and requires a fresh independent review of the final integrated source.
Quick, Standard and Extended modes keep the lightweight solo loop.

## What changed since 0.2.0

- **Team mode** in `SKILL.md`, with [orchestration](../../skills/sdlc-flow/references/orchestrate.md),
  [shared memory](../../skills/sdlc-flow/references/shared-memory.md) and
  [host mapping](../../skills/sdlc-flow/references/host-adapters.md) playbooks.
- **Optional record helper** `scripts/team.py` (Python 3.9+, standard library only):
  canonical task state, owner and generation checks, stale-result and stale-evidence
  rejection, context packets, checkpoints, and a completion gate bound to the current
  source and requirements. Worker results may omit unknown model metadata.
- **Completion and scope rules**: before reporting, list the changed paths as
  version control reports them and check them against the request's path limits;
  any source change after the independent review goes back to a reviewer; a worker
  result counts as integrated only after its canonical transition succeeds; worker
  status describes the worker's own slice.
- **Claude Code guidance**: Agent descriptions as task names, background workers when
  the orchestrator must keep working, explicit worker models, sandbox liveness limits.

## Qualification

The released package is byte-identical to the qualified candidate
`0.3.0-team.7` except for its version string. Full method, identities and
superseded candidate history are in [Claude Code qualification](claude-qualification.md).

- **Recovery**: one product task across an initial session and ten fresh root
  sessions on Claude Code (`claude-sonnet-5-5`), covering completed-worker recovery,
  a failed command, a killed root process, three requirement changes, rejection of a
  stale gate, a worker kept live across a session boundary, and a final independent
  review. All 11 sessions and all 10 resets passed.
- **Correctness pilot**: two real libraries (TinyDB, python-dotenv) at pinned upstream
  revisions, two repetitions each. All four runs passed every product check; three of
  four passed independent review of tests, documentation, final-source review,
  routing and scope.
- **Package**: validator, 24 helper tests, evaluator self-test, clean copy install for
  Codex and Claude Code, and Ubuntu/macOS/Windows CI.

## Known limitations

- In one pilot run the orchestrator listed its changed paths but kept an
  out-of-scope `CHANGELOG.md` edit and reported it as documentation. The scope rule
  allows "revert or report"; tightening it to revert is planned for a later release.
- Qualification covers one host and model (Claude Code with Sonnet 5.5) and two
  bounded Python tasks. It is controlled fresh-session recovery, not native context
  compaction. No speed, cost, or superiority claim over other workflows is made.
- Codex support is documented and was exercised in earlier phases, but the full
  recovery and pilot gates were qualified on Claude Code.
- Workers often still use fixed scratch names under the system temp directory despite
  the per-role scratch guidance.
