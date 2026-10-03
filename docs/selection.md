# Source and workflow selection

SDLC Flow is a single instruction skill. Its ordinary path is one coding agent working in short, checkable slices. It writes persistent task state only when interruptions or coordination make recovery costly. Additional agents and specialized tools can help when available, but the core path uses common file, search, shell, and project tools.

This choice follows the [Agent Skills format](https://agentskills.io/specification): one `SKILL.md`, focused references loaded when relevant, and assets copied with the skill. It is a workflow design, not a measured claim that this package outperforms another agent setup. A skill can guide an agent; it cannot enforce a controller's phase transitions or retries.

| Source considered | Portable contribution | Packaging decision |
| --- | --- | --- |
| [Addy Osmani Agent Skills](https://github.com/addyosmani/agent-skills) | Dependency-aware planning; reproduce and localize defects; code and UI review dimensions. | Four pinned prose snapshots included. Our references adapt the ideas without fixed file paths or cross-skill calls. |
| [Superpowers](https://github.com/obra/superpowers) | Fresh verification before completion claims. | One pinned prose snapshot included. Our review path sizes checks to the actual claim and risk. |
| [Anthropic Frontend Design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) | Subject-specific visual direction and self-critique. | Pinned prose snapshot included for new visual direction, alongside our product and accessibility checks. |
| [planning-with-files](https://github.com/OthmanAdi/planning-with-files) | File-based task memory across context resets. | One original task-state template included. Its hooks and mandatory multi-file workflow are not part of this package. |
| Controller-based workflows, including the author's local `devflow` | Enforced stages, retries, and routing can suit large managed environments. | No controller dependency. A plain Agent Skill cannot promise those enforcement guarantees. |
| [Impeccable](https://github.com/pbakaus/impeccable), [Vercel interface guidance](https://github.com/vercel-labs/web-interface-guidelines), [OpenSpec](https://github.com/Fission-AI/OpenSpec), [GSD](https://github.com/gsd-build/get-shit-done) | Useful specialized methods. | Their CLI, hook, or runtime fetch patterns were not necessary for the first one-install release. They can be evaluated as optional future additions. |

The exact redistributed files, commits, SHA-256 digests, and licenses are in [SOURCES.lock.json](../skills/sdlc-flow/SOURCES.lock.json) and [THIRD_PARTY_NOTICES.md](../skills/sdlc-flow/THIRD_PARTY_NOTICES.md). Vendored snapshots retain original text and may contain links or commands from their upstream collections. The runnable workflow lives in the self-contained root skill and its references.

## Review criteria for future additions

Add an upstream source only when it changes a decision the current skill handles poorly, its license and transitive files are understood, and it can be included without a runtime download or host-specific setup. Keep only one installer-visible `SKILL.md`. A new module should have an explicit routing condition from the root skill and a clean-install check proving all referenced files ship together.
