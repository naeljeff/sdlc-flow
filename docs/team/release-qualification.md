# Release qualification

Qualification started on 2026-10-05 from commit `7438335`, package
`0.3.0-team.3`. Implementation publication is separate from release acceptance.
The candidate remains a development version until the critical gates below have
current evidence. A missing measurement does not become zero or a passing result.

## Preflight hardening: team.4

Independent release inspection reproduced three helper defects before new model
subjects were launched:

- Multiline worker next actions and accepted fact text could forge Markdown rows
  in generated status/memory views. Generated text is now rendered as one literal
  line, escaping controls and Markdown syntax while preserving canonical JSON.
- A freshly filtered context packet still advertised an older `facts.json`
  projection. It now supplies a fresh `status` command for broader retrieval and
  no projection path; callers use only currently validated facts.
- Immutable artifacts were written directly to their final names. Interrupted
  writes could leave partial checkpoint files. They now publish a flushed temp
  file with an exclusive atomic hard link, preserving existing immutable content.
  Filesystems without hard-link support fail closed rather than weakening the
  no-overwrite guarantee; the manual host-file protocol remains available.

The new regressions exercise projection forgery, dereferencing stale memory,
partial serialization/retry and conflicting immutable contents. All 23 helper
and probe tests, package validation and evaluator self-test pass locally. Independent
review reproduced the fixes. GitHub Actions run `37283527189` passed installation
and Ubuntu/macOS/Windows validation, including Python 3.9 artifact publication. The
recovery and current pilot must use the new `0.3.0-team.4` package; these unit
checks do not establish their behavioral outcomes.

| Gate | Required evidence | Current status |
| --- | --- | --- |
| Package and helper | Self-contained install; meaningful lifecycle, scope, freshness and artifact checks; independent review | team.4: 23 tests, independent review, clean install and Ubuntu/macOS/Windows CI passed |
| Fresh-session recovery | Frozen initial session plus ten fresh sessions, requirements changes, interruption, stale gate rejection, dirty preservation, live-worker ownership and final integrated review | New team.4 assessment frozen; independent exact-hash review pending |
| Current matched pilot | Same source, requirements, model policy and independent outcome review for current candidate and baseline | team.4 versus `dev` frozen; 14 controls passed; independent preflight pending |
| Devflow comparison | Actual controller and native routes, isolated task/configuration, same product acceptance; no existing solution supplied | Capability and isolation assessment underway; no current comparative result |
| Broader task coverage | New source-bound software tasks with observable public outcomes and independently checked graders | Not yet qualified beyond bounded Python library pilot |
| Workflow accounting | Retained failed attempts, root/worker/reviewer coverage, observed timing and usage without duplicate totals | Full workflow metrics remain unknown; no speed/token/cost superiority claim |
| Host support | Real coding workflow on each advertised host, with actual permissions and route observations | Codex native routing observed; Claude evidence limited to scoped probe |
| Stable publication | Current critical gates, exact version/tag, clean install, documented limitations and reversible local update | Not yet eligible |

## Execution rules

Freeze each subject's package, task source, route, graders and adaptations before
launch. Require independent preflight of the exact identities. Keep private
prompts, graders, controls, sessions and account metadata outside the repository.
Subjects receive public requirements and source, never another workflow's patch
or the hidden expected solution. Preserve every attempt and distinguish product
failure, harness failure and provider/capability failure.

If qualification reveals a defect, first reproduce the violated invariant,
correct the generic mechanism, and rerun affected checks. Freeze a new candidate
before a new behavioral attempt; do not rewrite an old result into a pass.
Evaluator fixes require independent review and controls proving that the same
behavioral acceptance still rejects targeted failures.

The new recovery preflight reproduced a legacy evaluator path mismatch: a valid
canonical inbox result was rejected where the older alternate-path fixture was
accepted. The new assessment uses the helper's actual result path, recognizes
literal static RTK proxy commands, and checks observed terminal ownership across
deferred ingestion. Product acceptance IDs and phase prompts remain unchanged;
49 existing lifecycle controls retain their expected outcomes, with ten added
protocol equivalence and negative controls. This establishes harness mechanics,
not a recovered native product trajectory or a retrospective subject pass.

Production eligibility requires packaging/helper correctness and current full
recovery plus the current correctness pilot on the declared host. Comparative
superiority, native compaction and every possible framework are separate claims
that require their own evidence. Unsupported host capabilities must remain
explicit. Broader coverage and metrics qualify the advertised scope rather than
adding runtime dependencies to the installed skill.

## Current position

Independently audit the frozen recovery assessment with team.4, then run
the unchanged behavioral trajectory. Prepare the matched pilot and Devflow
capability checks in parallel. Do not tag a stable release while the critical
recovery gate remains unproven.
