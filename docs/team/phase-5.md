# Phase 5: Matched correctness pilot

**Status: completed with one routing failure; performance superiority not established.**

## Scope and controls

The frozen pilot compared the SDLC Flow development candidate with the standalone
`dev` skill on two bounded Python library changes: TinyDB and python-dotenv. Each
arm had two fresh runs per task, for eight planned subject runs total. All used
the same requested native Codex model and concurrency policy. The exact workflow
copies, task briefs, graders, run records, and reviewer receipts are retained in
the private evaluation workspace; this public report excludes those materials.

The pilot used the frozen `0.3.0-team.1` candidate. The published `0.3.0-team.3`
package includes later phase-4 recovery and helper lifecycle corrections; those
changes were not included in these matched subject runs and have not received a
new matched correctness pilot.

The independently approved preflight verified 14/14 product controls and the
runner checks. Every completed subject passed its automated product checks, and
all eight independent reviews passed the task-specific test/documentation
criterion. The separate routing review found seven compliant runs and one
violation. Reviewers were bound to each final source snapshot and preserved their
initial assessments and evidence-only follow-ups.

Several initial routing reviews were false negatives because their evidence
packets omitted exact assignment or copy/workdir metadata. Those initial verdicts
remain recorded; the same assessors changed them only after source-bound,
evidence-only supplements established the missing facts. One run still failed
after this check because its worker had written outside its assigned paths.

## Results

| Task | SDLC Flow candidate | `dev` |
| --- | --- | --- |
| TinyDB | 2/2 objective passes | 2/2 objective passes |
| python-dotenv | 2/2 objective passes | 1/2 objective passes |
| Total | 4/4 | 3/4 |

The failing `dev` run passed its product tests and documentation review, but its
`feature_b` worker created `tests/test_alternate_variables.py` outside the
assignment's explicit owned paths. No permission amendment was evidenced, and
later integration did not retroactively authorize that write. The independent
review therefore rejected its routing check. This is a real run failure, not a
grader or packet-preparation correction.

The eight subject rows required 15 attempts because explicit usage-limit and
model-capacity failures were preserved and retried under the same frozen model
and task. The third TinyDB candidate attempt produced the reviewed result; prior
failed attempts remain in the private record.

## Limits

This was a small correctness pilot, not a direct comparison with Devflow. The
standalone `dev` skill was the baseline. It does not establish statistical
superiority, faster delivery, lower token use, or lower cost. The report has
root-attempt durations, but full workflow time and descendant usage were not
observed, so they remain unknown. The pilot also does not test ten-session
recovery; that remains Phase 4's separate gate.

The descriptive result is 4/4 candidate objective passes and 3/4 `dev` passes.
The single out-of-scope write is actionable evidence for stronger assignment
boundary enforcement and review packet completeness, but is not enough to claim
general superiority.

## Reproduction boundary

The exact pilot manifest and runner hashes, independent preflight receipt,
per-run review decisions, failed attempts, and report are preserved outside the
public skill package. The broad 40-run bank remains blocked. No raw task prompts,
hidden graders, local transcripts, or account usage records are published.

After publication, the current repository package passed the Skill Hub install
smoke test from both a local checkout and GitHub. The GitHub Actions run for the
phase-4 commit passed the package install job and Linux, macOS, and Windows
validation jobs. The global Codex and Claude Code copies were then updated to
`0.3.0-team.3` and individually validated against the repository; complete
`0.2.0` backups were retained locally. This verifies packaging and installation,
not the recovery behavior described in Phase 4.
