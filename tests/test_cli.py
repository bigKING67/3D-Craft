from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "3d-craft" / "scripts" / "3d_craft.py"


class ThreeDCraftCliTests(unittest.TestCase):
    def run_cli(self, *arguments: str, expected: int = 0) -> dict:
        result = subprocess.run(["python3", str(CLI), *arguments, "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_route_selects_bridge_references_and_gates(self) -> None:
        payload = self.run_cli("route", "--target", "bridge", "--intent", "build", "--profile", "product-asset", "--quality-tier", "production", "--authoring-mode", "hybrid", "--evidence-level", "assured")
        self.assertEqual(payload["schema"], "3d-craft.route.v1")
        self.assertIn("gltf-web-handoff.md", payload["selected_references"])
        self.assertIn("web_runtime", payload["hard_gates"])
        self.assertIn("browser.capture", payload["required_capabilities"])

    def test_static_blender_route_excludes_browser(self) -> None:
        payload = self.run_cli("route", "--target", "blender", "--evidence-level", "static")
        self.assertNotIn("browser.capture", payload["required_capabilities"])
        self.assertNotIn("gltf", payload["hard_gates"])

    def test_init_run_requires_absolute_explicit_directory(self) -> None:
        result = subprocess.run(["python3", str(CLI), "init-run", "--project-key", "fixture", "--run-dir", "relative", "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be absolute", result.stderr)

    def test_init_run_creates_external_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = self.run_cli("init-run", "--project-key", "fixture", "--run-dir", directory)
            run = json.loads((Path(directory) / "run.json").read_text())
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(run["schema"], "3d-craft.run.v1")
            self.assertLessEqual(len(run["repairs"]), 3)
            self.assertTrue((Path(directory) / "evidence").is_dir())

    def test_validate_requires_hash_verified_fixed_view_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            assets = run_dir / "assets"
            evidence = run_dir / "evidence"
            assets.mkdir()
            evidence.mkdir()

            def write_json(path: Path, value: dict) -> None:
                path.write_text(json.dumps(value), encoding="utf-8")

            def file_entry(path: Path, value: bytes) -> dict:
                path.write_bytes(value)
                return {"path": str(path), "sha256": hashlib.sha256(value).hexdigest()}

            source = run_dir / "source.py"
            source.write_text("# fixture\n", encoding="utf-8")
            blend_file = assets / "asset.blend"
            blend_file.write_bytes(b"blend")
            glb_file = assets / "asset.glb"
            glb_file.write_bytes(b"glb")
            glb_hash = hashlib.sha256(b"glb").hexdigest()
            write_json(run_dir / "run.json", {"repairs": [], "unverified": []})
            write_json(run_dir / "scene.json", {"schema": "test.scene"})
            write_json(run_dir / "asset.json", {"source": {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}})
            write_json(evidence / "blend-inspection.json", {"status": "PASS", "coverage": {"components_percent": 100, "materials_percent": 100}})
            write_json(evidence / "reproduction.json", {"match": True})
            write_json(evidence / "gltf-validation.json", {"validator": {"issues": {"numErrors": 0}}, "semantic": {"bytes": 3, "triangles": 1}})

            views = []
            for view in ("front", "back", "left", "right", "top", "perspective"):
                views.append({"view": view, **file_entry(evidence / f"{view}.png", view.encode())})
            render_manifest = {
                "status": "PASS",
                "views": views,
                "contact_sheet": file_entry(evidence / "contact.png", b"contact"),
                "lookdev": file_entry(evidence / "lookdev.png", b"lookdev"),
            }
            write_json(evidence / "render-evidence.json", render_manifest)
            screenshot = file_entry(evidence / "browser.png", b"browser")
            write_json(evidence / "browser-runtime.json", {
                "status": "ready",
                "console_errors": 0,
                "asset": {"sha256": glb_hash},
                "network": {"status": "PASS"},
                "raf": {"delta": 1},
                "metrics": {"draw_calls": 1, "textures": 1, "frame_p95_ms": 8},
                "cross_runtime": {"required_node_coverage_percent": 100, "bbox_drift_percent": 0},
                "desktop_screenshot": screenshot,
            })

            passing = self.run_cli("validate", "--run-dir", str(run_dir))
            self.assertEqual(passing["status"], "PASS")
            (evidence / "front.png").write_bytes(b"tampered")
            failing = self.run_cli("validate", "--run-dir", str(run_dir), expected=2)
            self.assertEqual(failing["status"], "FAIL")
            identity = next(item for item in failing["gates"] if item["id"] == "identity")
            self.assertEqual(identity["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
