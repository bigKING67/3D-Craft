#!/usr/bin/env python3
"""Validate the source tree or one installed 3d-craft Skill without third-party Python packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_skill(skill: Path, errors: list[str]) -> None:
    skill_file = skill / "SKILL.md"
    if not skill_file.is_file():
        fail(errors, f"missing {skill_file}")
        return
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) > 500:
        fail(errors, f"SKILL.md exceeds 500 lines: {len(lines)}")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        fail(errors, "SKILL.md frontmatter is missing")
    frontmatter = text.split("---", 2)[1]
    allowed_frontmatter = {"name", "description", "license", "allowed-tools", "metadata"}
    top_level_keys = set(re.findall(r"(?m)^([A-Za-z0-9-]+):", frontmatter))
    unexpected_keys = top_level_keys - allowed_frontmatter
    if unexpected_keys:
        fail(errors, f"unsupported top-level SKILL.md frontmatter fields: {sorted(unexpected_keys)}")
    for field in ("name:", "description:", "license:", "metadata:"):
        if not re.search(rf"(?m)^{re.escape(field)}", frontmatter):
            fail(errors, f"SKILL.md missing frontmatter field {field[:-1]}")
    if not re.search(r"(?m)^  compatibility:\s+\S", frontmatter):
        fail(errors, "SKILL.md metadata.compatibility is required")
    if not re.search(r"(?m)^name:\s+3d-craft\s*$", frontmatter):
        fail(errors, "Skill name must be 3d-craft")
    version = (skill / "VERSION").read_text(encoding="utf-8").strip() if (skill / "VERSION").is_file() else ""
    if not version or f'version: "{version}"' not in frontmatter:
        fail(errors, "Skill VERSION does not match metadata.version")
    openai_yaml = skill / "agents" / "openai.yaml"
    if not openai_yaml.is_file() or "$3d-craft" not in openai_yaml.read_text(encoding="utf-8"):
        fail(errors, "agents/openai.yaml missing or default prompt does not mention $3d-craft")
    required_refs = {"authority-and-evidence.md", "blender-production.md", "gltf-web-handoff.md", "web3d-runtime-qa.md", "repair-and-security.md"}
    actual_refs = {path.name for path in (skill / "references").glob("*.md")}
    if required_refs != actual_refs:
        fail(errors, f"reference set mismatch: expected={sorted(required_refs)} actual={sorted(actual_refs)}")
    schema_ids = set()
    for schema_path in sorted((skill / "schemas").glob("*.json")):
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            fail(errors, f"invalid JSON {schema_path}: {error}")
            continue
        schema_id = schema.get("$id")
        if not schema_id or schema_id in schema_ids:
            fail(errors, f"missing or duplicate $id in {schema_path}")
        schema_ids.add(schema_id)
    if len(schema_ids) != 4:
        fail(errors, f"expected four schemas, found {len(schema_ids)}")
    for script in ("3d_craft.py", "blend_inspect.py", "render_evidence.py", "gltf_validate.mjs"):
        if not (skill / "scripts" / script).is_file():
            fail(errors, f"missing Skill script {script}")
    viewer = skill / "assets" / "r3f-viewer"
    viewer_package_path = viewer / "package.json"
    viewer_lock_path = viewer / "package-lock.json"
    if not viewer_package_path.is_file() or not viewer_lock_path.is_file():
        fail(errors, "viewer package.json and package-lock.json are both required")
    else:
        viewer_package = json.loads(viewer_package_path.read_text(encoding="utf-8"))
        viewer_lock = json.loads(viewer_lock_path.read_text(encoding="utf-8"))
        locked_root = viewer_lock.get("packages", {}).get("", {})
        if viewer_package.get("version") != version or locked_root.get("version") != version:
            fail(errors, "viewer package and lock versions must match Skill VERSION")
        for dependency_group in ("dependencies", "devDependencies"):
            declared = viewer_package.get(dependency_group, {})
            locked = locked_root.get(dependency_group, {})
            if declared != locked:
                fail(errors, f"viewer {dependency_group} differ from the nested lockfile")
            for dependency, constraint in declared.items():
                if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", constraint):
                    fail(errors, f"viewer dependency must use an exact version: {dependency}={constraint}")
    forbidden_generated = [
        viewer / "node_modules",
        viewer / "dist",
        viewer / "tsconfig.tsbuildinfo",
        viewer / "public" / "asset.glb",
    ]
    for path in forbidden_generated:
        if path.exists():
            fail(errors, f"generated viewer artifact must remain outside the installable Skill: {path}")
    for path in skill.rglob("*"):
        if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}:
            fail(errors, f"generated Python artifact must remain outside the installable Skill: {path}")


def validate_root(root: Path, errors: list[str]) -> None:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    skill_version = (root / "skills" / "3d-craft" / "VERSION").read_text(encoding="utf-8").strip()
    if version != skill_version:
        fail(errors, "root VERSION and Skill VERSION differ")
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    if package.get("version") != version:
        fail(errors, "package.json version differs from VERSION")
    if package.get("pi", {}).get("skills") != ["skills/3d-craft"]:
        fail(errors, "package.json pi.skills must expose only skills/3d-craft")
    upstreams = json.loads((root / "upstreams.lock.json").read_text(encoding="utf-8"))
    for item in upstreams.get("upstreams", []):
        if not re.fullmatch(r"[a-f0-9]{40}", item.get("commit", "")):
            fail(errors, f"upstream {item.get('repo')} is not pinned to a full commit")
        if item.get("copied_files"):
            fail(errors, f"V0.1 must not copy upstream files: {item.get('repo')}")
    for script in ("install_local.sh", "package_skill.py", "release_gate.py"):
        if not (root / "scripts" / script).is_file():
            fail(errors, f"missing root release script {script}")
    for document in ("PRODUCT.md", "ARCHITECTURE.md", "MATURITY.md", "ROADMAP.md", "HOST_COMPATIBILITY.md"):
        if not (root / "docs" / document).is_file():
            fail(errors, f"missing product document {document}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    skill = Path(args.skill_root).expanduser().resolve() if args.skill_root else root / "skills" / "3d-craft"
    errors: list[str] = []
    validate_skill(skill, errors)
    if not args.skill_root:
        validate_root(root, errors)
    payload = {"schema": "3d-craft.source-validation.v1", "status": "PASS" if not errors else "FAIL", "skill_root": str(skill), "errors": errors}
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else f"{payload['status']}: {len(errors)} error(s)")
    for error in errors:
        print(error, file=sys.stderr)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
