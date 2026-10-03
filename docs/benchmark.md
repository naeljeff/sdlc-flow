# Paired behavioral benchmark

This is a reproducible **evaluation protocol**, not evidence that one skill is generally best. It tests whether a candidate SDLC Flow revision improves accepted solutions per total token on tasks it did not train against. It uses Python's standard library for the runner and whatever Python, Node.js, or Go runtime a selected task already needs. The installed skill does not need this harness or any runtime dependency.

## Task portfolio

`tests/behavior/cases.py` defines twelve small cases in three stacks. The first four form a cheap canary; run it before the full portfolio.

| Set | Task | Stack | Failure family |
| --- | --- | --- | --- |
| Canary | `py-recovery-quantity` | Python | Interrupted work with an inaccurate progress claim and unrelated dirty file |
| Canary | `py-async-session` | Python | Stale success and stale error after a selected session changes |
| Canary | `js-account-cache` | JavaScript | Cross-account cache key collision |
| Canary | `go-money-overflow` | Go | Checked arithmetic boundary |
| Full | `py-pagination` | Python | Bounded slicing defect |
| Full | `py-protected-routes` | Python | Missing direct protected route and bearer validation |
| Full | `py-migration-repeat` | Python | Idempotent data migration and preservation |
| Full | `js-safe-retry` | JavaScript | Bounded retries without write replay |
| Full | `js-status-ui` | JavaScript | Accessible status and escaped item text |
| Full | `js-listener-cleanup` | JavaScript | Subscription lifecycle |
| Full | `go-cursor-page` | Go | Cursor exclusivity and terminal page |
| Full | `go-config-precedence` | Go | Layered precedence and input preservation |

Each case has an agent-visible `TASK.md` and starting source. The grader is kept by the operator under `tests/behavior/` and is only copied into a temporary directory **after** the candidate is frozen. It is absent from both agent workspaces. This separation prevents accidental answer copying during a disciplined run; it is not an access-control boundary. Once the benchmark repository is public, its fixture and grader code can be inspected or memorized, so use new private holdouts for release decisions.

The reference patch is for validating the grader, not for agent prompts. Run:

```sh
python3 tests/behavior/benchmark.py selftest --set canary
python3 tests/behavior/benchmark.py selftest --set full
```

The required result for every task is `unchanged=FAIL reference=PASS`. If either side is wrong, repair or drop the fixture before running an agent. These are narrow unit and behavior checks; they do not replace full integration or deployed checks in a real project.

## Paired run

Freeze two skill directories before preparing a run: one released baseline and one candidate. Both arms must use the **same model, reasoning effort, tools, task prompt, starting commit, time limit, and retry policy** for each paired task. Randomize which arm runs first; repeat the portfolio across seeds and at least one lower-cost and one stronger model before concluding that a rule generalizes.

```sh
python3 tests/behavior/benchmark.py prepare \
  --set canary \
  --out /absolute/path/to/new-benchmark-run \
  --old-skill-path /absolute/path/to/baseline/sdlc-flow \
  --new-skill-path /absolute/path/to/candidate/sdlc-flow
```

`prepare` refuses an existing output path. It creates `manifest.json` with task IDs, paths, skill tree hashes, one shared Git base commit per task, the hash of each identical initial tree (including dirty overlay), and grader hashes. For each task, give an agent only that arm's workspace path, its `TASK.md`, and its assigned skill path from the manifest. The agent should work only inside that workspace. Do not point the agent at `cases.py`, grader code, reference patches, prior solutions, or another arm's checkout. A pre-run prompt audit should reject any path to those artifacts. Use a fresh session for each arm and task.

The runner does not launch an LLM. That keeps model choice and tool logs explicit. Capture each attempt's Codex CLI JSON event stream. After every attempt, even a failed or blocked one, record it:

```sh
python3 tests/behavior/benchmark.py record-attempt \
  --manifest /absolute/path/to/new-benchmark-run/manifest.json \
  --task py-async-session --arm new \
  --events /absolute/path/to/attempt.jsonl \
  --status completed --model gpt-6-luna --effort low \
  --duration-seconds 48.2
```

The recorder sums every `turn.completed` usage block in that event stream. `input_tokens` already includes cached input; `cached_input_tokens` is retained separately for analysis and is not added twice. If a failed attempt has no usage event, its token total is **unknown**, not zero. If a run requires a repair attempt, record both attempts. The comparison denominator includes every recorded attempt, including failures and blocks.

When implementation stops, freeze the workspace **before** grading it:

```sh
python3 tests/behavior/benchmark.py freeze --manifest /absolute/path/to/new-benchmark-run/manifest.json --task py-async-session --arm new
python3 tests/behavior/benchmark.py grade  --manifest /absolute/path/to/new-benchmark-run/manifest.json --task py-async-session --arm new
```

`freeze` requires the original HEAD, records Git status and the tracked binary patch hash, and saves a full source snapshot outside the agent workspace. That snapshot captures task files and untracked implementation files too. `grade` reads the frozen snapshot in an isolated temporary copy and leaves the candidate untouched. Re-running `grade` replays the same frozen candidate; a changed workspace cannot silently change a published result. Use a new run directory for a new candidate revision.

After both arms have frozen snapshots, grader results, and attempt receipts for each task:

```sh
python3 tests/behavior/benchmark.py compare --manifest /absolute/path/to/new-benchmark-run/manifest.json
```

`compare` checks skill hashes, shared base commits, frozen/graded tree hashes, and per-task model and effort equality. It reports accepted solutions, all attempts' token totals, and **tokens per accepted solution**. Missing receipts leave token efficiency unmeasured; never infer zero cost. Report correctness and safety failures separately from cost. A lower token number cannot redeem an incorrect or unsafe patch.

## Release decision and limits

Use the four-task canary to reject obvious regressions cheaply. Run the broad portfolio only if the canary is acceptable. For a change to the workflow text, keep the old and new skill trees immutable during each paired run; report both hashes, model/effort, prompt policy, task order, failed attempts, median and tail tokens, and wall time. Inspect failures to identify *which decision* failed, then design a general rule and test it against new holdouts rather than writing a rule that names a single product or API.

These twelve cases are intentionally small and synthetic. They establish grader discrimination (`unchanged=FAIL reference=PASS`) and offer repeatable comparisons, but do not measure long-horizon delivery, repository navigation, native UI, deployment, security review, or all possible user requests. Their solutions are visible in this repository, so the public cases are canaries and regression checks, not private proof of broad reliability. For a release claim, add blind tasks from multiple real projects and task families, independent reviewers, and follow-up checks in the actual runtime. Report the sampling limits and uncertainty rather than treating a finite benchmark as universal coverage.
