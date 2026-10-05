# Team orchestration implementation ledger

This work implements the approved parallel-delivery proposal in phases. Baseline: `cbf362f` / SDLC Flow 0.2.0. Candidate version: `0.3.0-team.4`. The earlier precedence experiment and benchmark evidence remain separate. Phase completion records describe actual evidence rather than planned capabilities. Current release gates are tracked in [release qualification](release-qualification.md).

| Phase | Scope | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Team workflow, ownership, shared memory, native model capability contract | Complete | Package validation, whitespace check, independent review with both blockers fixed; see [phase 1](phase-1.md) |
| 2 | Optional stdlib state helper, contracts, freshness, contextual handoffs | Complete | 15 macOS tests, independent adversarial review, package validation; see [phase 2](phase-2.md) |
| 3 | Native heterogeneous routes and capability probes | Complete with host limits | Codex causal heterogeneous overlap verified; initial Claude headless profile blocked; 19 local tests and independent runner review; see [phase 3](phase-3.md) |
| 4 | Integration and long-session recovery | Implementation updated; fresh qualification in progress | Earlier v2.5.1 stopped at phase 0. Current team.4 assessment passed phases 0–4, then stopped at the stale-rejection observation gate in phase 5. Observer false negative independently established; fresh v2.7 then stopped at phase 0 on a separately classified stdout-wrapper mismatch. Both failures retained; v2.8 observer independently approved; fresh phases 0–4 passed, phases 5–10 pending. See [phase 4](phase-4.md) and [release qualification](release-qualification.md) |
| 5 | Matched evaluation, clean install, local package update | Complete with one routing failure; performance superiority not established | Frozen `0.3.0-team.1` pilot: 4/4 candidate vs 3/4 standalone `dev` objective passes, with 7/8 routing checks; GitHub and local Skill Hub copies of `0.3.0-team.3` validated. The updated phase-4 behavior was not in the pilot; see [phase 5](phase-5.md) |

## Publication policy

Each phase is documented, checked, committed, and pushed to this repository. A pushed development phase is not a stable release or proof of performance superiority. Private task state, account configuration, prompts containing local data, and raw sessions stay outside the public package. Publish only sanitized evidence summaries and reproducible checks.

## Phase 1 review disposition

Independent review found optional self-review and solo status-file recovery could bypass Team gates. Both were corrected in the entrypoint and references. No remaining instruction-contract blocker. Assignment/result templates move to Phase 2 so their fields are validated against the actual helper rather than creating competing schemas. Runtime model selection, isolation, and recovery remain unproven until their phases.
