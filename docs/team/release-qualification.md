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
| Fresh-session recovery | Frozen initial session plus ten fresh sessions, requirements changes, interruption, stale gate rejection, dirty preservation, live-worker ownership and final integrated review | team.4 v2.6 passed phases 0–4, then stopped on redirected stderr; v2.7 stopped at phase 0 on stdout-wrapper observation; both independently classified; v2.8 independently preflighted and fresh full execution authorized |
| Current matched pilot | Same source, requirements, model policy and independent outcome review for current candidate and baseline | Twelve-run original plan; first candidate independently accepted after an evidence-gap reassessment; four native and one adapted run pass automated checks; current fresh reviews authorized |
| Devflow comparison | Actual controller and native routes, isolated task/configuration, same product acceptance; no existing solution supplied | Default controller context bound blocked implementation; a separate operationally adapted four-run cohort has passed independent preflight; no completed comparative result |
| Broader task coverage | New source-bound software tasks with observable public outcomes and independently checked graders | Two new TypeScript/Go holdouts; corrected graders and twelve controls independently approved; actual native execution driver and reviewer entrypoint independently approved; two fresh candidate-only runs queued |
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

The first five recovery stages passed. The new root
recovered the completed canonical inbox results without replacing the original
Records/Store workers, integrated the dependent writer, and obtained independent
review. Current acceptance, evidence freshness, isolation and the preserved
dirty note passed at that boundary. An intentional failed command was diagnosed
from the native exit status, and the supervisor then interrupted a real root
process after its durable checkpoint marker. Changed-requirement recovery also
passed. This is five stages of eleven, not full
long-session qualification or native context compaction evidence.

The current matched study uses the same root/reviewer Sol-high and implementation
Astra-high profile across SDLC Flow, standalone `dev`, and the actual Devflow
controller. Capacity is three for every arm; actual scheduling may differ. The
Devflow runtime and policy are isolated privately, with a real three-role native
capability proof before launch. Fourteen task controls and independent exact-hash
preflight passed. This protocol has twelve product runs; it has no completed
comparative outcome yet and does not measure general superiority. The first
candidate run passed its deterministic product checks. Its first independent
assessment was negative because the reduced packet could not establish worker
ownership; that result is retained. After independently audited provenance
collection and study binding, a fresh assessment accepted the same frozen source.
This is an evaluator reassessment, not first-assessment success or another solver
attempt. Reviewer packet preflight caught raw tool arguments
and insufficient same-run snapshot binding before any judge launch. The approved
packet builder now supplies only the public brief, current final source and
structured route/scope observations bound to that run's receipts.

The additional holdouts cover reentrant Zustand state subscriptions and HTTP
`Vary` header composition in Go CORS middleware at pinned upstream revisions.
Initial holdout grader inspection found two false-positive risks: default
equality could masquerade as configured equality, and a header union could alter
first-occurrence spelling/order or retain empty directives. The revised probes
and targeted mutations now reject those cases. Twelve baseline, positive and
negative controls passed independent replay; the original public requirements,
source snapshots and acceptance IDs remain unchanged. The execution manifest, native runner and runnable reviewer entrypoint have
passed independent exact preflight; two fresh candidate-only runs are authorized
and queued. No holdout subject has launched. The
TypeScript probe is not browser or visual UI evidence. The author's broader read
of the public evaluator API exceeded the initial narrow read instruction; this
was disclosed, with no evidence that private historical solutions or candidate
outcomes entered the authored tasks.

## Current stop and operational adaptations

Recovery v2.6 stopped automatically at phase 5: Priority, Status and dirty
preservation passed, but `STALE_REJECTED` did not. The native protected-helper
command exited 2 and saved its error text through redirection. The evaluator
expected that text in the raw tool output, which was empty. The original failed
receipt and report remain unchanged. Independent inspection established an
observer false negative: the source-bound helper rejected the same-task obsolete
revision, emitted the required marker to redirected stderr, and left the gate
unaccepted. The private observer was corrected to capture native-event-bound redirected
evidence, with targeted positive and negative controls. It retains all 95 earlier
predicate outcomes and 14 product controls, with 33 additional redirected-output
controls. Independent exact preflight passed, and a fresh full eleven-stage
trajectory was authorized. The old phase was not rescored or resumed. Phases
6–10 of v2.6 have not launched. Full recovery remains a release blocker.

The default Devflow controller stopped before implementation when a required
16,926-character context packet exceeded its unchanged installed 16,000-character
bound. A second repetition was paused after architecture started, with cleanup
and all attempts retained. These are controller capability/interruption results,
not completed-patch accuracy measurements. Further known-blocked default runs
are deferred. A supplemental four-run Devflow cohort passed independent exact preflight with
only the private context bound raised to 1,000,000 characters, leaving these fixed
tasks unbounded by that guard. It retains the source, requirements, models,
effort and controller, and starts from fresh contexts/source without the paused
plan. Its outcomes must be reported separately from the original study. The
first adapted run has now finished and passed all automated product checks; independent outcome
review remains pending. No global Devflow installation or policy is changed.

Do not tag a stable release while the critical recovery gate remains unproven.

## Subsequent observation checks

The independently approved fresh v2.7 trajectory stopped at phase 0 after 584.1
seconds: startup and dirty preservation passed, but its completed-pending
observation failed. Both exact native workers terminated, their canonical states
were recorded as not live, and their correct result files remained un-ingested.
Independent inspection found the Records worker's native tool output contained
bytes identical to its canonical result; a transparent `text(r.output)` wrapper
had omitted the nested exit metadata expected by the observer. The public prompt
required printing identical JSON, not a separately exposed nested exit status.
The frozen failed grade remains unchanged. The approved v2.8 observer recognizes
that source-bound stdout pattern while leaving unobserved exit status unknown.
All 128 previous predicate outcomes and 14 product controls were preserved, and
54 new stdout controls passed independent preflight. A fresh full trajectory is
authorized; these mechanics do not establish its behavioral result. No later v2.7 phase launched.

Independent packet audits also rejected incomplete controller route coverage
before judging. The new approved collector reconciles complete attempt receipts
with bounded native root/descendant metadata, checks rooted parent graphs and
ordered lifecycle intervals, and reports missing evidence as incomplete. Forty-two
controls cover duplicate/conflicting attempts, cyclic/orphan parent edges,
omitted descendants, missing inventory, reversed timestamps and capacity. Native and controller packets supply the same required host-inventory and
lifecycle evidence. Duplicate native descendant IDs are rejected before role
mapping. Exact generic, original-study and supplemental-study bindings passed
independent inspection and actual provider-free approval gates. A dependency-key
serialization mismatch was caught before any judge started; new immutable
receipts corrected it, retaining the earlier receipts and rejected launch. The collector sends the public brief, final source and safe route
metadata; prior negative assessments remain retained. Native host observations do
not attest upstream provider identity, dynamic mutation scope or shared-workspace
byte authorship.

## Controller retry disposition

The second adapted TinyDB run completed eight architecture calls, each rejected
by the official plan validator because the plan listed `git` as a verification
runner. Its candidate fingerprint and accepted-plan state did not advance. The
controller's continuous mode removed attempt limits; its repeated-failure check
compared varying artifact bytes before the common diagnostic, allowing identical
semantic rejections to retry indefinitely. The operator used the official pause
and owned-process cleanup, preserving all eight completed attempts and the ninth
interrupted attempt. This post-launch operational stop is disclosed separately
from product accuracy; no completed patch is graded for that row.

For a later controller row showing the same established blocker, three consecutive
completed architecture calls with the identical rejection and no source or plan
progress trigger the same official pause and cleanup. This is a disclosed stop
for a known endless operational loop, not a token ceiling or a rescued solver.
The next adapted task progressed to implementation after its second architecture
attempt without changes to source, prompts, models or controller policy.
