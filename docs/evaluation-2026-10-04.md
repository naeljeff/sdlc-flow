# Evaluation record: SDLC Flow 0.2.0

This record separates a **blind skill comparison** from later independent review and repair. It is evidence for this release, not a claim that one instruction package is best for all software tasks. The runner and task definitions are described in [benchmark.md](benchmark.md).

## General task portfolio

The same model, effort, tools, starting fixture, task prompt, and retry policy were used for both skill arms of each case. The old and new installed skill tree SHA-256 values were `9b47a03de957ebd127c220b3cad54d31e298e0cc8ae31a9c2f6bc00bb5c777e7` and `1d23592e5e80e78a547a4b1439aee7f8b4b2db3a2ef7cfd55bffb56cbd1bc263`. Every unchanged fixture failed its grader and every reference patch passed before agent runs. The graders stayed outside the agent workspaces until patches were frozen. These fixtures and graders are public in this repository, so they are regression canaries rather than private holdouts.

| Run | Model and effort | Old accepted | 0.2.0 accepted | Old total tokens | 0.2.0 total tokens | Old uncached input + output | 0.2.0 uncached input + output |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 12-task portfolio | `gpt-6-luna`, low | 12/12 | 12/12 | 2,567,418 | 2,611,963 | 273,146 | 240,123 |
| 4-task canary | `gpt-6.1-sol`, high | 4/4 | 4/4 | 725,416 | 791,521 | 109,096 | 156,513 |

The four canary tasks are part of the twelve-task portfolio, not an independent sample. The candidate used 1.7% more total tokens on the full low-effort run while using 12.1% fewer uncached input plus output tokens. On the stronger-model canary it used 9.1% more total tokens and 43.5% more uncached input plus output. Cached input dominates the total-token counter, so both measures matter. This does **not** establish a general efficiency or correctness win.

## Real issue replay

We replayed [ByteTrade issue #143](https://github.com/naeljeff/byteTrade-tauri/issues/143) from web commit `4caa23f8f01bc63fb34c385dd0b54e2e1f7a5a03`, with contract commit `0d83b049ab061c41b1967019b212e969b9be6447`. Both old and 0.2.0 arms used `gpt-6.1-sol` at high effort and the same prompt bytes (SHA-256 `b157c8024c99e76d830ce5eaa9396b4e23098122c90442f62161bad7ecc89499`). The prompt excluded PR #144, previous candidates, their reports, and other issue worktrees. Command traces showed no access to those materials. Each patch was frozen before evaluator tests.

| Blind run | Common REST holdout | Supplemental WS diagnostic | Shell commands | Total input + output tokens | Uncached input + output |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.1.0 | 3/3 | 0/2 | 193 | 8,659,399 | 263,111 |
| 0.2.0 | 3/3 | 1/2 | 141 | 7,936,759 | 294,647 |

The WS diagnostic was written after reviewing the first candidate. It tests same-session credential rotation and frames decoded after a socket is retired; it is **not** an unbiased part of the original REST holdout. The 0.2.0 blind run fixed the delayed-frame case but still left an old socket open after same-session token rotation. Its total token count fell 8.3%, while uncached input plus output rose 12.0%; it took about 20 minutes versus an approximately 18-minute-51-second older process-log span. These are single-run observations with cache and runtime variation, not a pricing or latency guarantee.

Independent source review of the frozen 0.2.0 patch found three more gaps: a smart-order poll could delete a newer WS-only plain order; real-book fills had lost their portfolio refresh event source; and by-id ownership preflight errors lost the gateway's `result` field. These were repaired and tested in a **separate reviewed pass**. That pass is not counted as blind skill performance or token efficiency. It reached 3/3 REST, 2/2 WS, and passing independent registry and auth/write holdouts, with 375 focused tests, typecheck, scoped Biome, and diff checks. Its rollout-mode fixture varies mock behavior only for `enforce`, so it does not prove invalid or revoked token behavior under `optional`. The ByteTrade change was not tested against an authenticated live gateway or native Tauri runtime.

The historical scheduled [PR #144](https://github.com/naeljeff/byteTrade-tauri/pull/144) is a separate Codex automation output. No Devflow invocation was observed in its recorded trace. The independently attempted Devflow controller stopped in stage S2, so it had no completed end result to score as Devflow. Neither PR #144 nor the older candidate was used as source for the 0.2.0 implementation.

## Interpretation

The skill remains a small, installable instruction package. It improves the odds of asking about boundaries, transitions, and evidence, but cannot enforce a lifecycle or guarantee that a model catches every failure. A failed independent-agent invocation during the real replay illustrates that a skill cannot make unavailable host capabilities reliable. Use selective independent review for consequential cross-boundary work and report its extra cost separately. More private, cross-project tasks and authenticated runtime checks are needed before any broad performance claim.
