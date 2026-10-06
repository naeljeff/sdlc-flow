# Claude Code qualification for 0.3.0

**Status: final `0.3.0-team.7` runs in progress; results below are filled in as
each gate completes.**

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
| team.7 | In progress | In progress | Concrete pre-report scope check from version-control paths, worker slice-status semantics, assigned checks confirmed runnable, verbatim path limits for reviewers |

## Limits

This is controlled fresh-session recovery on one host and model, not native
context compaction. The pilot covers two bounded Python library tasks with one
workflow; it makes no comparison with `dev` or Devflow and no speed or cost
claim. Grader checks cannot detect deliberately fabricated evidence; the
evaluator-path check inspects tool inputs, not results.
