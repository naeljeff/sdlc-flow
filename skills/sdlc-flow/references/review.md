# Review the actual diff and completion evidence

For Team mode, review the integrated candidate in a fresh independent context. Give the reviewer current acceptance IDs, constraints, the permitted and preserved paths as the request states them, combined diff, source identity, and raw evidence rather than your conclusions about it. Provide the reviewer its own disposable copies of the candidate and of the starting revision (for example via `git worktree add`) for probes and base comparisons, and tell it to leave the integration workspace's files, index, refs, and stash unchanged. Verify combined behavior beyond the workers' local checks; renew affected review evidence after source or requirements change. Worker completion and a reviewer's approval sentence do not establish acceptance by themselves.

In solo mode, review in proportion to the change. For substantial or high-risk work, do this explicitly before claiming completion; a separate reviewer is optional when an independent context would materially help. Team mode follows the independent gate above.

Use an independent reviewer when a consequential failure could hide in a state transition, boundary, or end-to-end path that the implementer has not independently checked. Give the reviewer the acceptance criteria, changed diff, relevant context, and specific unresolved invariant; ask for plausible counterexamples, not a rerun of the same green checks. Prefer one review of the integrated behavior unless separable slices each carry material risk. If delegation costs more than its likely new evidence, perform the same adversarial check yourself.

## Diff review

- Compare against the task's starting revision: list every changed path, confirm each is permitted, and confirm preserved and unrelated paths are unchanged.
- Execute each changed code or command example and check each changed concrete documentation claim against the candidate; record any that cannot run here as unverified.
- Trace changed behavior through callers, validation, persistence, transport, and UI rather than judging only the edited function.
- Look for incorrect assumptions, missing cases, data loss, races, unsafe input handling, widened authorization, secrets, and dependency or configuration changes.
- For changes on trust boundaries, follow input from source to sink and check authentication, authorization, validation, and error handling at the actual enforcement point. For performance-sensitive paths, inspect likely hot paths and measure before claiming an improvement.
- Check that new tests exercise the reported symptom or acceptance path and that they could fail for a broken implementation. Run mutation or other destructive probes only in disposable copies, and count a mutant only after confirming its diff is non-empty.
- For stateful or cross-boundary changes, challenge the planned invariants and checks for omitted material failure modes, including changed state, delayed work, partial results, and error translation. Check that the final evidence reaches the caller or user, not just the edited component.
- Remove unnecessary abstractions, dead code, and scope expansion. Explain any material concern left open.

## Evidence review

Run the checks relevant to the final diff. Record command, result, revision/files, and limitation. Prefer the cheapest check that catches a likely error first; add integration, build, browser/device, or deployment evidence when the requirement needs it. A passing local test does not prove production, native-device, or authenticated behavior. Use fresh output after the final edit; do not promote an earlier green result into completion evidence. When the project's native runner is unavailable, run the same substitute on a separate base copy and on the candidate and report the difference as non-native evidence. Record a missing tool as a capability limit and continue with available checks; install or download tools only when the user or project rules authorize it.

Treat another agent's review as a finding to verify, not as an approval receipt by itself. Apply worthwhile fixes, rerun affected checks, and distinguish unresolved findings from false positives with reasons. Report the verified result and remaining gaps plainly.

For substantial reviews, the bundled [review source](../vendor/addy/review.md) expands the dimensions to inspect. The bundled [verification source](../vendor/superpowers/verification.md) is useful when claims and check provenance are getting muddled; read it as guidance, not as a requirement to run every available suite.
