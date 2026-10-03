# Plan only as far as the work needs

Use this when the task has several steps, uncertain scope, or meaningful dependencies. Begin with the user's outcome and the product's current behavior. In an existing codebase, identify the affected callers, contracts, and tests before committing to file names or architecture. In a new project, choose the smallest runnable slice that demonstrates the main user journey before adding infrastructure.

## A useful plan

State:

- Observable acceptance criteria and the original symptom, if any.
- Constraints from the user, project instructions, API/contracts, and existing changes.
- Ordered, end-to-end slices; for each, the user-visible or API outcome and a check capable of detecting a likely failure.
- Dependencies, critical path, and genuinely independent branches. Keep interface or data contract decisions ahead of dependent implementation.
- Assumptions that need a probe before implementation.

For a slice involving state over time or component boundaries, state what must remain true for the caller or user across each material changed boundary or transition. Choose a small, risk-ranked set of nonredundant counterexamples from changed identity or state, delayed or reordered work, partial success, unavailable dependencies, invalid input, and errors whose meaning changes across layers. Use the cheapest observable check that could expose each distinct high-risk failure mode before marking the slice verified; one check may cover several modes. Do this once at planning or when a new boundary appears, not on every tool call. A bounded, well-understood calculation needs no extra matrix.

Use a few lines in chat for a short task. For an extended task, put milestones in its task-local state. A separate plan file helps only when the dependency graph no longer fits there. Do not expand a small edit into phases just to fill a template.

Before execution, challenge the plan: Is any step speculative? Does it repeat a component or abstraction already present? Is a supposed contract only an assumption? Would a narrower change meet the acceptance criteria? Does each slice leave a testable result rather than separate unfinished frontend and backend pieces? If a critical assumption fails, revise the plan and the task state before continuing.

Approval belongs to the user's request and project rules. Research or proposal work can stop at a reviewable design when that is what the user asked for; ordinary authorized implementation can continue through verification.

The bundled [planning source](../vendor/addy/planning.md) gives a more detailed dependency breakdown when a large task warrants it. Treat its fixed file paths as examples; this skill uses task-local state only when needed.
