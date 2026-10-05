"""Release identity checks: a tag must never validate a different package."""
import tempfile
import unittest
from pathlib import Path

from validate_package import Checks, validate_frontmatter


class ReleaseIdentityTests(unittest.TestCase):
    def check_version(self, version_line, expected):
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "sdlc-flow"
            skill.mkdir()
            (skill / "LICENSE").write_text("MIT", encoding="utf-8")
            (skill / "SKILL.md").write_text(
                "---\nname: sdlc-flow\ndescription: Develop software\nlicense: MIT\n"
                "metadata:\n" + version_line + "\n---\n", encoding="utf-8")
            checks = Checks()
            validate_frontmatter(skill, checks, expected)
            return checks.errors

    def test_exact_release_and_development_versions(self):
        for version in ("0.3.0", "0.3.0-team.4"):
            self.assertEqual(self.check_version(f'  version: "{version}"', version), [])

    def test_tag_cannot_accept_development_package(self):
        errors = self.check_version('  version: "0.3.0-team.4"', "0.3.0")
        self.assertTrue(any("release version mismatch" in error for error in errors))

    def test_missing_duplicate_or_malformed_version_rejects(self):
        for line in ("", "  version: 0.3.0\n  version: 0.3.0", "  version: 03.0.0"):
            self.assertTrue(self.check_version(line, "0.3.0"))


if __name__ == "__main__":
    unittest.main()
