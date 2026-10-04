# Phase 1: explicit team delivery contract

This phase changes the skill's behavior for tasks that benefit from substantial independent work or explicitly request multiple agents. Solo work keeps its small common loop. Team work now follows a concrete scheduling, memory, ownership, and integration procedure.

## Shipped changes

- The entrypoint selects Team mode and requests native delegation with one orchestrator.
- `orchestrate.md` defines the dependency board, work ownership, isolated edits, integration, and completion gate.
- `shared-memory.md` defines accepted task knowledge, worker inboxes, revisioned context packets, freshness, and recovery.
- `host-adapters.md` maps native host capabilities and model selection to the common protocol, with honest unavailable-route behavior.
- Planning, review, and long-task references connect to the team workflow. No new vendored sources or licenses are introduced.

## Concrete decomposition example

For an existing application's inventory dashboard, first establish the current pagination/data contract and effective acceptance IDs. Assign the shared API/schema contract to one owner. Once its shape is established, an inventory feature worker owns its route/service/tests, a saved-filter feature worker owns its independent route/service/tests, and an investigation worker checks compatibility with existing consumers. Writers use separate snapshots and workspaces; read-only investigation may share the integration checkout.

When a worker discovers an incorrect pagination assumption, it submits the source and counterexample. The orchestrator publishes the verified correction to common task memory and updates affected assignments. A completed filter slice is integrated while the inventory worker continues. Final evidence exercises filtering with pagination on the combined candidate, then an independent reviewer checks omitted states and preserved behavior. Individual green suites alone cannot close the product task.

This example establishes assignment boundaries and a real integration gate. It is a design walkthrough, not measured runtime or speed evidence.

## Validation

The package validator passed with local runtime links and pinned upstream hashes intact. `git diff --check` passed. Independent protocol review is recorded in the implementation ledger before publication. Helper automation, live model routes, and fresh-session recovery belong to subsequent phases and are not claimed by this phase.

## Host sources

The native mappings are grounded in the official [Codex subagent documentation](https://developers.openai.com/codex/subagents) and [Claude Code subagent documentation](https://code.claude.com/docs/en/sub-agents). Runtime tool schemas and account capability still determine what actually works. The [Agent Skills specification](https://agentskills.io/specification) allows supporting references and executable helpers within one installed folder.
