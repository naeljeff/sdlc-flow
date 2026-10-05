# Stable release procedure

Stable publication is blocked until the current critical gates in
[release qualification](release-qualification.md) pass. These steps prepare an
exact release; they do not declare the development candidate qualified.

## Prepare and verify

1. Record the accepted package commit, current recovery trajectory, final product
   assessments, declared host scope and remaining limitations. Keep private
   sessions, graders and account metadata outside the public repository.
2. Change the skill's `metadata.version` to the intended stable version. Compare
   the entire installable directory with the qualified candidate: every byte must
   match except that one version value. If any operational file changes, qualify
   the changed behavior before promotion. Publish both identities and the exact
   comparison result in the release report.
3. On the release commit, run package validation with `--expected-version`, the
   helper tests, release-identity tests, evaluator self-test and clean copy-install
   smoke test. Require the exact commit's cross-platform and installation CI.
   Tag CI also requires the packaged version to equal the tag without its `v`.
4. Create the version tag on that verified commit. Verify its commit identity and
   CI before publishing a GitHub release containing the sanitized qualification
   report. A Git tag by itself is not evidence of release acceptance.

For the proposed `v0.3.0`, the release-identity check is:

```sh
python3 tests/validate_package.py --expected-version 0.3.0
python3 -m unittest discover -s tests -p 'test_validate_package.py' -v
```

## Verify distribution

The ordinary `naeljeff/sdlc-flow` source follows the repository's default branch.
For reproducible installation, test the full GitHub skill-tree URL containing the
release tag with the normal skills CLI in a disposable project, then verify the
installed version and every installed file against the release package. The tag
route must be tested after the tag exists; it is not currently a published release.

```sh
bash tests/smoke_install.sh \
  https://github.com/naeljeff/sdlc-flow/tree/v0.3.0/skills/sdlc-flow 0.3.0
```

Run this command from the exact release checkout. The smoke test copies the
complete skill for Codex and Claude Code without global installation and compares
both copies with that checkout's package, ignoring only generated Python caches.
Its version check also establishes release identity. Installation on Claude is
not evidence of a complete native Claude team coding workflow.

## Local update and rollback

Before an authorized global update, copy each currently installed skill directory
to a new dated backup and record its file hashes. Do not rely on an older backup
whose contents differ from the current installation. Use the verified source
with the ordinary skills CLI and `--copy`; verify both installed directories
against the release package. Keep host/provider configuration unchanged.

If verification fails, restore each directory from its corresponding fresh
backup and verify the restored hashes. Preserve the failed installation and its
diagnostic evidence outside discoverable skill directories. Record the tested
source, version, package identity and rollback location in the release report.
