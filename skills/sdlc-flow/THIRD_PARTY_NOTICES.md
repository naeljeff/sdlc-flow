# Third-party source notices

SDLC Flow includes the following unchanged upstream prose snapshots for attribution and optional deeper reading. They have been renamed from `SKILL.md` so they do not appear as separate installable skills. The operational instructions in this package's root `SKILL.md`, `references/`, and `assets/` are self-contained; the snapshots do not need to be loaded or executed for SDLC Flow to work.

| Source | Snapshot in this package | License |
| --- | --- | --- |
| [Addy Osmani Agent Skills](https://github.com/addyosmani/agent-skills/tree/a06bc63b3f8b829c14b0bbf53d99fefc39d58092) | [`vendor/addy/planning.md`](vendor/addy/planning.md), [`debugging.md`](vendor/addy/debugging.md), [`review.md`](vendor/addy/review.md), [`frontend.md`](vendor/addy/frontend.md) | [MIT](vendor/addy/LICENSE) |
| [Superpowers](https://github.com/obra/superpowers/tree/8ca22dba9a94f28898bbce59f2537ff4d87c747d) | [`vendor/superpowers/verification.md`](vendor/superpowers/verification.md) | [MIT](vendor/superpowers/LICENSE) |
| [Anthropic Frontend Design](https://github.com/anthropics/skills/tree/8a1541c4a3ffa5a20a5a91de0dcf3f0bab1d1ef4/skills/frontend-design) | [`vendor/anthropic/frontend-design.md`](vendor/anthropic/frontend-design.md) | [Apache-2.0](vendor/anthropic/LICENSE.txt) |

`SOURCES.lock.json` records every original path, pinned Git revision, bundled path, and SHA-256 digest. Each license file is included unchanged. The Addy and Superpowers snapshots originated within larger skill collections; their cross-skill calls, relative links, sample commands, and host-specific steps describe those upstream collections. They are background material, not SDLC Flow setup requirements. Some links inside the flattened snapshots refer to upstream files that are not bundled. Use the self-contained operational references for the runnable workflow.

This package does not include upstream hooks, controllers, binaries, or scripts. No source snapshot author is represented as endorsing SDLC Flow.
