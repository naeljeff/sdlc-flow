# Phase 3: native host execution and evidence

The installed skill uses the host's native delegation and available model controls. The source repository adds standard-library probe and evaluation runners; they are development tools and are unnecessary for normal skill installation. No provider credentials or global configuration are written.

## Observed host profiles

Capability observations are specific to this installed host/account, not universal product promises. Fresh route probes succeeded on Codex and Claude Code. Codex root metadata reports the requested `gpt-6.1-sol`. Claude's configured root route reported a different alias/provider identity; authentication alone did not prove an Anthropic model.

A Codex native probe launched two workers before waiting. Both consumed the same packet, preserved the dirty draft, and returned tool intervals overlapping by approximately 1.005 seconds. Structured native spawn records establish delegation. Initial spawn responses did not expose child identities. Read-only inspection of the host's exact parent-child edges recovered the two child session IDs. Their own `turn_context` records report `gpt-6.1-sol` and `gpt-6-astra`; each child trace contains its own successful command with the PID and packet hash in the matching result file. Independent review verified this causal chain. This establishes native heterogeneous execution at **host-reported route scope**, not cryptographic upstream-provider identity. Unrelated conversation contents were not read. The optional metadata reader treats absent/changed host schemas as unknown.

Claude's initial headless profile started native agents with `sonnet`/`haiku` requests, but their shell actions were denied because no permission-prompt responder was available. That profile did not establish useful worker overlap. A separate narrowly authorized tool profile may be assessed; it cannot erase the failed profile or silently change the backend.

## Runner review

Independent review found that an exit-zero CLI could be recorded as successful despite an exact requested model mismatch, and that recovery approvals were not bound to the actual phase specification. These launch gates were corrected before scoring. Root identity and worker identity are separate: unknown or substituted exact routes fail the automated gate. Model-set presence does not establish role compliance; each scored result also requires independent role/concurrency review. Recovery has a separate specification-bound review gate. Logical isolation also does not prove graders are unreadable; assessment controls remain outside all subject paths and traces need contamination review.

The reviewed runner hashes are `cdd72a4da24a140ad0c682f924b5e14d70b43025d8d1be8ff4f8c91f3d249e69` (`probe.py`) and `f8a8190c8e244fd9815cba333e3ffb89f141bebadf9d9656beec29981a5a77f6` (`evaluate.py`). Four structured-receipt regressions plus 15 state tests pass locally, and the mechanical integration self-test rejects a composed defect, crashed grader and dirty mutation. The independent preflight approved exactly eight fresh correctness sessions with frozen assessment/arms/routes. This is launch approval, not a passing benchmark result.

Observed versions: Codex CLI `0.159.3`, Claude Code `2.1.267`, macOS. [Runner commands](../../tests/team/README.md) and the [assessment protocol](evaluation-protocol.md) distinguish private controls from public tooling. Full-workflow usage remains unknown where descendant/reviewer coverage is unavailable. Native compaction is unobserved.
