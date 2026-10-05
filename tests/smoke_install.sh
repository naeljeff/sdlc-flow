#!/usr/bin/env bash
set -euo pipefail

# Installs only into a disposable project. Nothing is written to the user's
# global agent directories. Pass a GitHub source to test distribution of this
# exact checkout's package; the default tests the local checkout.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source="${1:-$repo_root}"
expected_version="${2:-}"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT
mkdir -p "$test_root/project"
cd "$test_root/project"

npx --yes skills@latest add "$source" --skill sdlc-flow -a codex -a claude-code --copy -y

for installed in "$test_root/project/.agents/skills/sdlc-flow" "$test_root/project/.claude/skills/sdlc-flow"; do
  test -f "$installed/SKILL.md"
  python3 "$repo_root/tests/validate_package.py" --skill-dir "$installed"
  if [[ -n "$expected_version" ]]; then
    python3 "$repo_root/tests/validate_package.py" --skill-dir "$installed" --expected-version "$expected_version"
  fi
  diff -qr -x __pycache__ -x "*.pyc" "$repo_root/skills/sdlc-flow" "$installed"
done

printf 'OK: Codex and Claude Code project copies contain the complete sdlc-flow bundle\n'
