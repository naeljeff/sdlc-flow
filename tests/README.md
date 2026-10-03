# Package checks

These checks are for package development. Installing or using `sdlc-flow` does not require Python, Node.js, or this test directory.

From the repository root:

```sh
python3 tests/validate_package.py
bash tests/smoke_install.sh
```

The validator checks the single skill entrypoint, required metadata, local links, bundled licenses, and every vendored file against `SOURCES.lock.json`. It checks the repository README and source-selection document when run without arguments. Original links inside vendored snapshots are excluded because those files preserve their upstream context and are not runtime playbooks.

The smoke test asks the skills CLI to copy the local package into a disposable project for Codex and Claude Code. It compares both installed copies with the source and deletes the disposable project afterward. It never installs into global agent directories.

After publishing, check the GitHub install path too:

```sh
bash tests/smoke_install.sh naeljeff/sdlc-flow
```

`tests/behavior/setup_fixtures.sh` creates two isolated Git repositories for qualitative agent evaluation: a bounded pagination bug and a cold resume with a stale task-state claim and an unrelated dirty file. Pass a new directory, such as the output of `mktemp -d`, and give each repository to a fresh agent with `$sdlc-flow`. These are deliberately failing fixtures, not an automatic pass/fail suite. The observed first-run results and limits are recorded in [validation.md](../docs/validation.md).
