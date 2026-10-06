# Claude Code qualification for 0.3.0

**Status: both gates passed on `0.3.0-team.7`.** Full eleven-session recovery
passed (11/11 sessions, 10/10 fresh resets); the correctness pilot produced 4/4
product passes and 3/4 objective passes, with one documented scope failure.

The Codex qualification left two release gates open: full eleven-session
recovery and a correctness pilot on the declared host. This record covers both
gates on Claude Code with `claude-sonnet-5-5` for every root session and every
Agent-tool worker. The private task sources, prompts, graders, controls, session
transcripts and receipts stay outside this repository; this report gives the
method, the identities that were bound, and the observed outcomes.

## Host route

- Claude Code 2.1.285, headless `claude --print --output-format stream-json`,
  one new session ID per root session, effort `high`.
- Workers are Agent-tool subagents; `CLAUDE_CODE_SUBAGENT_MODEL` pins them to the
  session model. Every run was checked from structured stream events: all root
  and worker assistant messages and the aggregated `modelUsage` reported only
  `claude-sonnet-5-5`.
- Subjects ran with an allow-listed environment (no inherited authentication,
  effort, proxy or model overrides), auto-memory off, no MCP servers, and no
  Workflow, artifact, web, cron or remote-trigger tools, in a disposable
  directory outside any folder with an ancestor `CLAUDE.md` or `AGENTS.md`.
- Recovery phases 7 and 8 must observe live processes with `ps`, which Claude's
  seatbelt sandbox hides, so subjects ran with that sandbox disabled. Protected
  paths outside the test roots (agent configuration, installed skills, this
  repository) were hashed before and after every batch; the only changes were
  the operator's own commits.

## Harness

The recovery trajectory reuses the Codex v2.8 scenario: the same Dispatch Ledger
source, eleven phases, acceptance IDs, unchanged product checks, and the same
runner. Host observations were ported from Codex session files to Claude
stream-json and live OS process state: worker identity and model from Agent
`tool_use` IDs and `parent_tool_use_id` events, lifecycle from
`task_started`/`task_notification`, helper receipts from each Bash call's own
result, liveness from `ps` and parent-PID chains, and release ordering from the
release file's creation time against the observing call's result timestamp.
Every requirement the grader enforces is stated in the public phase prompts.

Before any paid run, 14 product controls (identical expectations to the Codex
audit) and 54 host-observation controls passed, including real process-tree
checks. An independent reviewer audited the grader against the public prompts in
seven rounds; it found two blockers and nine major issues in the first two
rounds, all fixed before approval, and each later candidate was re-approved
bound to its exact manifest, specification and audit hashes.

The correctness pilot reuses the frozen team.4 pilot tasks (TinyDB and
python-dotenv at pinned upstream revisions, two repetitions each) with only the
route changed to Claude. Its 14-control audit matched the frozen Codex audit for
every candidate. Each run was also checked for evaluator-path access and for
Sonnet-only routing, and then received an independent outcome review of its
frozen final source for tests/documentation/final-source review and for
routing, scope and isolation.

## Candidate history

Each failure below was diagnosed to a generic workflow cause, fixed in the
skill, and the next candidate was re-qualified from a fresh trajectory and fresh
pilot subjects. Earlier results are retained as superseded evidence.

| Candidate | Recovery (fresh sessions) | Pilot | Defect found → fix |
| --- | --- | --- | --- |
| team.5 | Phases 0–7 passed; phase 8 failed: the fresh root applied the live worker's result to source but never recorded `transition --to integrated` | Automated 3/4; independent review 1/4 | Helper rejected worker results that omitted unknown metadata (found in harness review; fixed before runs). Runs showed edits after review without re-review, an out-of-scope `CHANGELOG.md`, a reviewer running `git stash` in the integration tree |
| team.6 | Phase 0 failed: a worker reported `partial` because its assigned check could not run and the result template modeled `partial` | Automated 3/4; independent review 3/4 | Post-review re-review fixed in 4/4 runs and docs examples executed in 4/4; one run kept `CHANGELOG.md` written through a `docs/` symlink |
| team.7 | First trajectory: phases 0–5 passed; phase 6 stopped because headless print mode killed the root's background reviewer 600 s after the root ended its turn (a harness setting; interactive sessions wait). Rerun with `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`: **all 11 sessions passed** | Automated 3/4; independent review 3/4 (objective passes recorded) | Concrete pre-report scope check from version-control paths, worker slice-status semantics, assigned checks confirmed runnable, verbatim path limits for reviewers |

## Final recovery: 0.3.0-team.7

Recovery manifest `eff4be2fd063eaf06e96d50e8e5cb5f6292d5dc1dd0d97a6e556587306bd6bdf`,
specification `7e489d969ac0bab1e74cf3e09bfbd6ff763826f986a2f5f4e8beb5f7901679df`,
control audit `2000e258d2d27a9b275073e503c5de930a61ef258b9ccbe915efa73b6a3acc57`,
task source `a524d3b8dd95a83497f10ec82e07ccf7eb402724b047a97d019e8f24cfefad19`.

| Phase | Scenario | Checks | CLI time | Reported cost |
| --- | --- | --- | --- | --- |
| 0 | Two workers complete; results saved but not ingested | BOOT, COMPLETED_PENDING, DIRTY | 340 s | $1.10 |
| 1 | Fresh root ingests original results, adds CLI writer, review, gate | 7/7 | 1214 s | $2.43 |
| 2 | Controlled failed command diagnosed | 6/6 | 112 s | $0.83 |
| 3 | Checkpoint, then the root process is killed | 3/3 | 64 s | interrupted |
| 4 | STATUS requirement change, writer, review, gate | 6/6 | 896 s | $1.70 |
| 5 | PRIORITY change; the old gate is rejected as obsolete | 4/4 | 310 s | $1.17 |
| 6 | All outcomes and review renewed; current gate | 4/4 | 315 s | $1.01 |
| 7 | EXPORT worker kept live across the session boundary | 5/5 | 279 s | $1.12 |
| 8 | Fresh root observes the live worker, releases it, ingests and integrates its original result, no replacement | 5/5 | 299 s | $0.66 |
| 9 | LIMIT change through a writer | 5/5 | 449 s | $1.34 |
| 10 | All seven acceptance IDs, independent reviewer runs helper status, current memory and constraints, gate | 13/13 | 1312 s | $2.69 |

Every root reported `claude-sonnet-5-5`. The report records all native root
receipts terminal, final evidence current for the final source, about 93 minutes
of root CLI time and $14.06 of reported cost; the interrupted phase-3 session
reports no usage, so the total is a lower bound. Protected paths outside the test
roots were unchanged apart from the operator's own commits.

## Final pilot: 0.3.0-team.7

Package tree `50c835c94c4f34ee6ea4352201c3e736aac8db7951be7fcd30ddf5d250638a61`
(commit `2e53354`), pilot manifest digest
`aa706730e566a875ab8b2629cb3ddc16443cdb2a7e225acc43d62e3ef0a7364a`, audit
`92557be8b16c625846eb8bcd0c0027132b56a74e7feb061f094fafba19f15f97`.

| Run | Product checks | Scope | Independent review | Objective pass | Time / reported cost |
| --- | --- | --- | --- | --- | --- |
| TinyDB 1 | T1–T4 pass | clean | T5 and ROUTE approved | yes | 584 s / $1.76 |
| TinyDB 2 | T1–T4 pass | clean | T5 and ROUTE approved | yes | 241 s / $1.17 |
| python-dotenv 1 | D1–D4 pass | clean | D5 and ROUTE approved | yes | 359 s / $1.27 |
| python-dotenv 2 | D1–D4 pass | `CHANGELOG.md` outside allowed paths | D5 approved, ROUTE rejected | no | 246 s / $1.03 |

Every run used two feature owners at the same time in their own copies, then an
independent reviewer of the integrated candidate; every post-review source
change went to a delta reviewer. All root and worker messages reported
`claude-sonnet-5-5`. The independent reviewer re-ran each snapshot's tests with
pytest, confirmed the new tests fail against the base revision and catch
targeted mutants, and executed the changed documentation examples.

The rejected run listed its changed paths before reporting, as the skill now
requires, but kept the `CHANGELOG.md` entry and reported it as documentation;
the skill's wording "revert or report" allowed that. The same repetition of this
task wrote `CHANGELOG.md` in all three candidates. That run also used
`git stash` in the integration tree to compare against the base revision,
leaving unreachable stash objects. Tightening the scope rule to revert
out-of-scope changes is a follow-up; it changes the package and needs a new
qualification.

## Limits

This is controlled fresh-session recovery on one host and model, not native
context compaction. The pilot covers two bounded Python library tasks with one
workflow; it makes no comparison with `dev` or Devflow and no speed or cost
claim. Grader checks cannot detect deliberately fabricated evidence; the
evaluator-path check inspects tool inputs, not results.
