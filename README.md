# SDLC Flow

One installable Agent Skill for software development from request to verified result. It gives a coding agent a small common loop and loads focused playbooks for planning, debugging, UI work, review, and long-task recovery only when they fit the task.

Version 0.3.0 adds an explicit Team mode: one orchestrator, native parallel workers, available model routing, common task knowledge, isolated code changes, and verification of the integrated product. It was qualified on Claude Code with Sonnet 5.5: an eleven-session fresh-session recovery passed every phase, and a correctness pilot on two real libraries passed every product check, with one documented scope failure. See the [Claude Code qualification](docs/team/claude-qualification.md), the [release notes](docs/team/release-0.3.0.md), and the [team ledger](docs/team/implementation.md). Performance superiority over other workflows is not claimed.

The skill uses the agent's ordinary tools. No separately installed controller, daemon, hook, MCP server, or second skill is required. Parallel agents and model choices use capabilities already exposed by the host; the skill does not supply models or authentication. Any upstream guidance used by the skill is included in the installed folder with provenance and licenses.

## Install

Install globally for Codex with the [skills CLI](https://github.com/vercel-labs/skills):

```sh
npx skills add naeljeff/sdlc-flow --skill sdlc-flow -g -a codex --copy -y
```

Install for Codex and Claude Code together:

```sh
npx skills add naeljeff/sdlc-flow --skill sdlc-flow -g -a codex -a claude-code --copy -y
```

For a project-only install, run the command in the project without `-g`. To inspect before installing:

```sh
npx skills add naeljeff/sdlc-flow --list
```

The installer is needed only to copy the package. After installation, the skill has no network or package-manager dependency of its own. Optional Team record automation uses an available Python 3.9+ interpreter and standard library; the host-file protocol remains available without it. The project being developed may, of course, have its own dependencies. You can also copy the entire `skills/sdlc-flow` directory into an agent's supported skills directory.

## Use

Invoke `$sdlc-flow` with your development request, for example:

```text
$sdlc-flow Fix the invoice rounding bug and verify the reported case.
$sdlc-flow Build a responsive settings page using this project's design system.
$sdlc-flow Continue the interrupted migration using the task state in this repo.
```

The skill chooses effort from the task's size and risk:

| Work | Default behavior |
| --- | --- |
| Bounded edit | Inspect, change, focused check. No task files by default. |
| Multi-step feature or defect | Short plan, end-to-end slices, relevant checks, and diff review. For stateful or cross-component work, use a small, risk-ranked set of checks for distinct failure modes across material changed boundaries or transitions. |
| Broad or interrupted task | One task-local `STATE.md` with compact per-slice status, acceptance evidence, ownership when delegated, and an exact next action. |
| Requested team or substantial independent slices | One orchestrator schedules bounded native workers, publishes accepted shared facts, integrates isolated changes, and obtains independent review of the combined outcome. |
| UI or high-risk change | Load the matching playbook and verify the visible path or trust boundary. |

Independent review is selective in solo mode. Team mode requires a fresh independent review of the integrated candidate. In solo mode, use it when another context is likely to find a consequential gap in a state transition, boundary, or user path. Ask for distinct counterexamples rather than another pass over the implementer's green checks. Keep progress checkpoints tied to verified slices, decisions, failures, and handoffs instead of logging every tool call.

The main entrypoint is [skills/sdlc-flow/SKILL.md](skills/sdlc-flow/SKILL.md). It links to the packaged references. [Source selection](docs/selection.md) explains the design choices, [initial validation evidence](docs/validation.md) records the first release checks, [benchmark method](docs/benchmark.md) describes repeatable cross-domain comparisons, and the [0.2.0 evaluation record](docs/evaluation-2026-10-04.md) reports the mixed results and limits. [Third-party notices](skills/sdlc-flow/THIRD_PARTY_NOTICES.md) and the [source lock](skills/sdlc-flow/SOURCES.lock.json) show the upstream material bundled in this release. The vendored files are optional source snapshots, not separately discoverable skills or runtime dependencies.

## Scope and evidence

SDLC Flow helps the agent make and verify decisions. An Agent Skill is an instruction package; it cannot enforce lifecycle steps the way a controller can. It asks for evidence appropriate to the task and distinguishes source inspection, local tests, browser or device observations, and deployed behavior. It does not treat a passing build or old test output as proof of a user-visible outcome.

The workflow is language and framework agnostic. Project instructions and the user's request decide whether work should stop at a proposal, continue to implementation, or include publishing. The skill does not require named roles or separate agents for routine work.

## Development and verification

The package has one installer-visible skill at `skills/sdlc-flow`. Files under `references/` and `assets/` are installed with it. See [tests](tests) for package checks and a clean-install smoke test. To validate locally from a checkout:

```sh
python3 tests/validate_package.py
```

The source lock pins each redistributed upstream file. Update a vendored file only alongside its lock entry and license notice. Keep the operational references self-contained: no installed user should need to fetch an upstream repository to complete a task.

## License

Original SDLC Flow content is MIT licensed. Bundled upstream files retain their own MIT or Apache-2.0 licenses; see [third-party notices](skills/sdlc-flow/THIRD_PARTY_NOTICES.md).
