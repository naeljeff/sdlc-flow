# Validation evidence for the initial release

This is a small release check, not a benchmark against other workflows. It verifies package shape, installer behavior, and two representative decisions. It does not establish that SDLC Flow is universally better than another skill or controller.

## Package and installation

| Check | Result |
| --- | --- |
| `uvx --from skills-ref agentskills validate skills/sdlc-flow` | Valid Agent Skill. |
| `python3 tests/validate_package.py --repo-root .` | One discoverable `SKILL.md`; local links, required license files, and pinned vendor SHA-256 digests valid. |
| `npx skills add . --list` | Discovered exactly one skill: `sdlc-flow`. |
| `bash tests/smoke_install.sh` | Installed complete, identical skill-folder copies into disposable Codex and Claude Code project locations. |

The package tests check files and installation. They do not prove that every agent will follow the instructions correctly.

## Independent forward test

The two initial fixtures are reproducible with [setup_fixtures.sh](../tests/behavior/setup_fixtures.sh). A separate agent read the skill and worked only in those isolated repositories.

| Task | Before | After | Decision observed |
| --- | --- | --- | --- |
| Five-item catalog, page two at two items per page | Public response returned `C, D, E`; focused test exited 1. | Public response returned `C, D`; 2/2 focused tests passed. | Reproduced the symptom and made a one-line slice fix without creating a task ledger. |
| Resume an interrupted invoice-quantity fix | State file claimed tests passed; fresh run failed because zero quantity returned 250 instead of 0. | Direct probe returned `[0, 250, 500]`; 3/3 tests passed. | Rechecked stale state, repaired the clamp, and preserved an unrelated dirty note. |

The forward test found that hidden `.sdlc-flow` files and untracked task files needed explicit discovery in the instructions; the skill was revised accordingly. The final skill revision has not been tested across many languages, UI stacks, or repeated long-horizon runs. Browser and deployed-runtime claims require separate evidence in each real project.

## Releasing a change

Run the reference validator, package validator, and disposable install smoke test after changing the skill. For a change to planning, debugging, UI, review, or resume decisions, add a focused forward test that could expose the new risk. Repeat the smoke test against `naeljeff/sdlc-flow` after publishing to prove the GitHub install path.
