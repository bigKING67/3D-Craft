from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGER = ROOT / "scripts" / "package_skill.py"


class PackagingTests(unittest.TestCase):
    def test_package_is_reproducible_and_contains_only_the_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packages = [root / "first.zip", root / "second.zip"]
            payloads = []
            for package in packages:
                result = subprocess.run(
                    ["python3", str(PACKAGER), "--output", str(package), "--json"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                payloads.append(json.loads(result.stdout))

            digests = [hashlib.sha256(path.read_bytes()).hexdigest() for path in packages]
            self.assertEqual(digests[0], digests[1])
            self.assertEqual(payloads[0]["sha256"], digests[0])
            with zipfile.ZipFile(packages[0]) as archive:
                names = archive.namelist()
            self.assertIn("3d-craft/SKILL.md", names)
            self.assertTrue(all(name.startswith("3d-craft/") for name in names))
            self.assertFalse(any("node_modules" in name or "/dist/" in name for name in names))

    def test_package_requires_an_absolute_output_path(self) -> None:
        result = subprocess.run(
            ["python3", str(PACKAGER), "--output", "candidate.zip", "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("absolute path", result.stderr)


if __name__ == "__main__":
    unittest.main()
