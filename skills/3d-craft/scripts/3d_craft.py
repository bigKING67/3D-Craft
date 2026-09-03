#!/usr/bin/env python3
"""Portable route, doctor, run initialization, and validation CLI for 3D-Craft."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "3d-craft.route.v1"
SKILL_VERSION = "0.1.0"
TARGETS = ("blender", "bridge", "web3d")
INTENTS = ("build", "validate", "repair")
PROFILES = ("product-asset", "prop")
QUALITY_TIERS = ("draft", "production")
AUTHORING_MODES = ("procedural", "native", "hybrid")
EVIDENCE_LEVELS = ("static", "rendered", "runtime", "assured")
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,95}$")
GATES = (
    "authority",
    "reproduction",
    "scene_integrity",
    "identity",
    "gltf",
    "cross_runtime",
    "web_runtime",
    "delivery",
)
STATUS_RANK = {"PASS": 0, "UNVERIFIED": 1, "BLOCKED": 2, "FAIL": 3}
FIXED_VIEWS = ("front", "back", "left", "right", "top", "perspective")
KNOWN_EVIDENCE = {
    "blend-inspection",
    "clean-reproduction",
    *FIXED_VIEWS,
    "contact-sheet",
    "lookdev",
    "visual-review",
    "gltf-validation",
    "browser-runtime",
    "browser-desktop-screenshot",
    "browser-mobile-screenshot",
}
CAPABILITIES = {
    "blender.version",
    "blender.inspect",
    "blender.execute",
    "blender.render",
    "blender.export",
    "asset.gltf.validate",
    "asset.gltf.inspect",
    "browser.navigate",
    "browser.capture",
    "browser.console.read",
    "browser.network.read",
    "browser.performance.profile",
}
GATE_STATES = {"pending", "running", "pass", "fail", "unverified", "blocked"}
HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def emit(payload: dict[str, Any], *, as_json: bool, output: str | None = None) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if output:
        target = Path(output).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded + "\n", encoding="utf-8")
    if as_json:
        print(encoded)
    else:
        print(f"3D-Craft {payload.get('command', 'result')}: {payload.get('status', 'ok')}")
        for key, value in payload.items():
            if key not in {"command", "status"}:
                print(f"{key}: {json.dumps(value, ensure_ascii=False)}")


def command_version(command: list[str], pattern: str | None = None) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if not executable:
        return {"status": "missing", "path": None, "version": None}
    try:
        result = subprocess.run(
            [executable, *command[1:]],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "unverified", "path": executable, "version": None, "error": str(error)}
    text = (result.stdout + "\n" + result.stderr).strip()
    version = None
    if pattern:
        match = re.search(pattern, text)
        version = match.group(1) if match else None
    elif text:
        version = text.splitlines()[0].strip()
    return {
        "status": "available" if result.returncode == 0 else "unverified",
        "path": executable,
        "version": version,
        "exit_code": result.returncode,
    }


def gltf_validator_probe(node: dict[str, Any]) -> dict[str, Any]:
    """Load the validator shipped with the Skill and return its observed version."""
    executable = node.get("path")
    script = Path(__file__).resolve().parent / "gltf_validate.mjs"
    if not executable or not script.is_file():
        return {"status": "missing", "path": str(script), "version": None}
    try:
        result = subprocess.run(
            [str(executable), str(script), "--doctor"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        payload = json.loads(result.stdout) if result.stdout else {}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return {"status": "unverified", "path": str(script), "version": None, "error": str(error)}
    return {
        "status": "available" if result.returncode == 0 and payload.get("status") == "PASS" else "unverified",
        "path": str(script),
        "version": payload.get("version"),
        "exit_code": result.returncode,
    }


def build_route(args: argparse.Namespace) -> dict[str, Any]:
    if args.target == "blender" and args.evidence_level == "runtime":
        raise ValueError("blender routes do not support runtime evidence; use static, rendered, or assured")
    if args.target == "web3d" and args.evidence_level == "rendered":
        raise ValueError("web3d routes do not support rendered-only evidence; use static, runtime, or assured")
    refs = ["authority-and-evidence.md", "repair-and-security.md"]
    capabilities: list[str] = []
    gates = ["authority", "delivery"]
    if args.target in {"blender", "bridge"}:
        refs.append("blender-production.md")
        capabilities.extend(["blender.version", "blender.inspect"])
        if args.intent in {"build", "repair"}:
            capabilities.append("blender.execute")
            if args.target == "bridge":
                capabilities.append("blender.export")
        gates.extend(["reproduction", "scene_integrity", "identity"])
        if args.evidence_level in {"rendered", "assured"}:
            capabilities.append("blender.render")
    if args.target in {"bridge", "web3d"}:
        refs.append("gltf-web-handoff.md")
        capabilities.extend(["asset.gltf.validate", "asset.gltf.inspect"])
        gates.append("gltf")
    if args.target in {"bridge", "web3d"} and args.evidence_level in {"runtime", "assured"}:
        refs.append("web3d-runtime-qa.md")
        capabilities.extend(
            [
                "browser.navigate",
                "browser.capture",
                "browser.console.read",
                "browser.network.read",
                "browser.performance.profile",
            ]
        )
        gates.extend(["cross_runtime", "web_runtime"])
    refs = list(dict.fromkeys(refs))
    capabilities = list(dict.fromkeys(capabilities))
    gates = [gate for gate in GATES if gate in set(gates)]
    return {
        "schema": SCHEMA_VERSION,
        "command": "route",
        "status": "ok",
        "target": args.target,
        "intent": args.intent,
        "profile": args.profile,
        "quality_tier": args.quality_tier,
        "authoring_mode": args.authoring_mode,
        "evidence_level": args.evidence_level,
        "selected_references": refs,
        "required_capabilities": capabilities,
        "hard_gates": gates,
        "unsupported_in_v0_1": [
            "reference-image-reconstruction",
            "character-production",
            "complex-animation-and-simulation",
            "games",
            "webgpu",
            "external-ai-3d-generation",
        ],
    }


def doctor_payload() -> dict[str, Any]:
    blender = command_version(["blender", "--version"], r"Blender\s+(\d+\.\d+\.\d+)")
    node = command_version(["node", "--version"], r"v(\d+\.\d+\.\d+)")
    npm = command_version(["npm", "--version"], r"(\d+\.\d+\.\d+)")
    python = {
        "status": "available",
        "path": sys.executable,
        "version": platform.python_version(),
    }
    blender_ok = blender.get("version") == "5.2.1"
    node_version = tuple(int(part) for part in (node.get("version") or "0.0.0").split(".")[:3])
    node_ok = node_version >= (22, 12, 0)
    gltf_validator = gltf_validator_probe(node) if node_ok else {"status": "unverified", "path": None, "version": None}
    gltf_ok = node_ok and gltf_validator.get("status") == "available"
    capabilities = {
        "blender.version": "available" if blender_ok else "unverified",
        "blender.inspect": "available" if blender_ok else "unverified",
        "blender.execute": "available" if blender_ok else "unverified",
        "blender.render": "available" if blender_ok else "unverified",
        "blender.export": "available" if blender_ok else "unverified",
        "asset.gltf.validate": "available" if gltf_ok else "unverified",
        "asset.gltf.inspect": "available" if gltf_ok else "unverified",
        "browser.navigate": "unverified",
        "browser.capture": "unverified",
        "browser.console.read": "unverified",
        "browser.network.read": "unverified",
        "browser.performance.profile": "unverified",
    }
    problems = []
    if not blender_ok:
        problems.append("Blender 5.2.1 LTS was not observed on PATH.")
    if not node_ok:
        problems.append("Node.js 22.12 or newer was not observed on PATH.")
    elif not gltf_ok:
        problems.append("The bundled Khronos glTF Validator runtime could not be loaded.")
    return {
        "schema": "3d-craft.doctor.v1",
        "command": "doctor",
        "status": "pass" if not problems else "partial",
        "skill_version": SKILL_VERSION,
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "tools": {"python": python, "node": node, "npm": npm, "blender": blender, "gltf_validator": gltf_validator},
        "capabilities": capabilities,
        "problems": problems,
        "notes": [
            "Browser capabilities require a live browser67 receipt and remain unverified here.",
            "Optional MCP availability is intentionally not required by V0.1.",
        ],
    }


def default_run_root() -> Path:
    configured = os.getenv("THREE_D_CRAFT_RUN_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "3d-craft" / "runs"
    state_home = os.getenv("XDG_STATE_HOME")
    if state_home:
        return Path(state_home).expanduser().resolve() / "3d-craft" / "runs"
    return Path.home() / ".local" / "state" / "3d-craft" / "runs"


def init_run(args: argparse.Namespace) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.project_key):
        raise ValueError("project-key must match ^[a-z0-9][a-z0-9-]{0,63}$")
    run_id = args.run_id or f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run-id must match ^[A-Za-z0-9][A-Za-z0-9_-]{7,95}$")
    if args.run_dir:
        run_dir = Path(args.run_dir).expanduser()
        if not run_dir.is_absolute():
            raise ValueError("--run-dir must be absolute")
        run_dir = run_dir.resolve()
    else:
        run_dir = (default_run_root() / args.project_key / run_id).resolve()
    if run_dir.exists():
        if not run_dir.is_dir() or any(run_dir.iterdir()):
            raise ValueError("run directory must be absent or empty; refusing to mix stale assets or evidence")
    for name in ("source", "assets", "evidence", "reports"):
        (run_dir / name).mkdir(parents=True, exist_ok=True)
    route_args = argparse.Namespace(
        target=args.target,
        intent=args.intent,
        profile=args.profile,
        quality_tier=args.quality_tier,
        authoring_mode=args.authoring_mode,
        evidence_level=args.evidence_level,
    )
    route = build_route(route_args)
    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run = {
        "schema": "3d-craft.run.v1",
        "run_id": run_id,
        "project_key": args.project_key,
        "created_at": created_at,
        "input_hashes": {},
        "route": {key: value for key, value in route.items() if key not in {"command", "status"}},
        "capabilities": {name: "unverified" for name in route["required_capabilities"]},
        "versions": {"3d-craft": SKILL_VERSION},
        "stages": [{"id": gate, "status": "pending"} for gate in route["hard_gates"]],
        "repairs": [],
        "evidence": [],
        "unverified": list(route["required_capabilities"]),
    }
    (run_dir / "run.json").write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "schema": "3d-craft.init-run.v1",
        "command": "init-run",
        "status": "pass",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "run_file": str(run_dir / "run.json"),
    }


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(root: Path) -> str:
    """Match the portable Skill tree digest emitted by install_local.sh."""
    digest = hashlib.sha256()
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(f"{sha256_file(path)}  ./{relative}\n".encode())
    return digest.hexdigest()


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def verified_file_entry(
    entry: Any,
    *,
    expected_path: Path | None = None,
    root: Path | None = None,
    require_bytes: bool = False,
) -> bool:
    """Verify a manifest file entry against the bytes on disk and an optional boundary."""
    if not isinstance(entry, dict):
        return False
    raw_path = entry.get("path")
    claimed_hash = entry.get("sha256")
    if not isinstance(raw_path, str) or not re.fullmatch(r"[a-f0-9]{64}", str(claimed_hash)):
        return False
    try:
        path = Path(raw_path).expanduser().resolve(strict=True)
    except OSError:
        return False
    if not path.is_file():
        return False
    if expected_path is not None:
        try:
            expected = expected_path.expanduser().resolve(strict=True)
        except OSError:
            return False
        if path != expected:
            return False
    if root is not None and not path_is_within(path, root.expanduser().resolve()):
        return False
    if require_bytes and entry.get("bytes") != path.stat().st_size:
        return False
    return sha256_file(path) == claimed_hash


def declared_file(asset: dict[str, Any] | None, expected_path: Path) -> dict[str, Any] | None:
    for entry in (asset or {}).get("derived", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            continue
        try:
            if Path(entry["path"]).expanduser().resolve(strict=True) == expected_path.resolve(strict=True):
                return entry
        except OSError:
            continue
    return None


def report_file_binding(report: dict[str, Any] | None, key: str, expected_path: Path) -> bool:
    entry = (report or {}).get(key)
    return verified_file_entry(entry, expected_path=expected_path)


def expected_route(route: Any) -> dict[str, Any] | None:
    if not isinstance(route, dict):
        return None
    dimensions = {
        "target": TARGETS,
        "intent": INTENTS,
        "profile": PROFILES,
        "quality_tier": QUALITY_TIERS,
        "authoring_mode": AUTHORING_MODES,
        "evidence_level": EVIDENCE_LEVELS,
    }
    if any(route.get(name) not in choices for name, choices in dimensions.items()):
        return None
    try:
        generated = build_route(argparse.Namespace(**{name: route[name] for name in dimensions}))
    except ValueError:
        return None
    return {key: value for key, value in generated.items() if key not in {"command", "status"}}


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def exact_keys(value: Any, allowed: set[str], required: set[str] | None = None) -> bool:
    return isinstance(value, dict) and set(value) <= allowed and (required or set()) <= set(value)


def as_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def nonempty_unique_strings(value: Any, *, allowed: set[str] | None = None) -> bool:
    return bool(
        isinstance(value, list)
        and value
        and all(isinstance(item, str) and item and (allowed is None or item in allowed) for item in value)
        and len(value) == len(set(value))
    )


def scene_contract_errors(scene: Any) -> list[str]:
    errors: list[str] = []
    required = {
        "schema", "units", "up_axis", "origin_policy", "topology_policy", "authoring_mode",
        "dimensions", "identity_features", "components", "materials", "cameras", "runtime",
        "budgets", "required_evidence",
    }
    if not exact_keys(scene, required | {"framing_center"}, required):
        return ["scene contract keys do not match scene.v1"]
    if scene.get("schema") != "3d-craft.scene.v1" or scene.get("units") != "meters" or scene.get("up_axis") != "Z":
        errors.append("scene schema, units, or up axis is invalid")
    if scene.get("origin_policy") not in {"object-base-center", "world-origin", "declared-custom"}:
        errors.append("scene origin_policy is invalid")
    framing_center = scene.get("framing_center")
    if scene.get("origin_policy") == "declared-custom" and not (
        isinstance(framing_center, list) and len(framing_center) == 3 and all(is_number(item) for item in framing_center)
    ):
        errors.append("declared-custom origin requires a finite three-number framing_center")
    if framing_center is not None and not (
        isinstance(framing_center, list) and len(framing_center) == 3 and all(is_number(item) for item in framing_center)
    ):
        errors.append("scene framing_center is invalid")
    if scene.get("topology_policy") not in {"closed", "open-allowed"}:
        errors.append("scene topology_policy is invalid")
    if scene.get("authoring_mode") not in AUTHORING_MODES:
        errors.append("scene authoring_mode is invalid")
    dimensions = scene.get("dimensions")
    if not exact_keys(dimensions, {"width", "depth", "height", "tolerance_percent"}, {"width", "depth", "height"}):
        errors.append("scene dimensions are malformed")
    else:
        if any(not is_number(dimensions.get(name)) or dimensions[name] <= 0 for name in ("width", "depth", "height")):
            errors.append("scene dimensions must be finite positive numbers")
        tolerance = dimensions.get("tolerance_percent")
        if tolerance is not None and (not is_number(tolerance) or tolerance < 0):
            errors.append("scene dimension tolerance is invalid")
    features = scene.get("identity_features")
    feature_ids: list[str] = []
    if not isinstance(features, list) or not features:
        errors.append("scene identity_features must be a nonempty list")
    else:
        for feature in features:
            if not exact_keys(feature, {"id", "description", "importance", "status"}, {"id", "description", "importance", "status"}):
                errors.append("scene identity feature is malformed")
                continue
            feature_id = feature.get("id")
            if not isinstance(feature_id, str) or not feature_id or not isinstance(feature.get("description"), str) or not feature["description"]:
                errors.append("scene identity feature text is invalid")
            else:
                feature_ids.append(feature_id)
            if feature.get("importance") not in {"critical", "major", "minor"} or feature.get("status") not in {"specified", "observed", "inferred", "unverified"}:
                errors.append("scene identity feature enums are invalid")
        if len(feature_ids) != len(set(feature_ids)):
            errors.append("scene identity feature IDs must be unique")
    if not nonempty_unique_strings(scene.get("components")):
        errors.append("scene components must be unique nonempty strings")
    if not nonempty_unique_strings(scene.get("materials")):
        errors.append("scene materials must be unique nonempty strings")
    if not nonempty_unique_strings(scene.get("cameras"), allowed=set(FIXED_VIEWS)) or set(scene["cameras"]) != set(FIXED_VIEWS):
        errors.append("scene cameras must contain the six fixed views exactly once")
    runtime = scene.get("runtime")
    if not exact_keys(runtime, {"engine", "renderer", "target_devices"}, {"engine", "renderer", "target_devices"}):
        errors.append("scene runtime is malformed")
    elif (
        runtime.get("engine") not in {"none", "three", "r3f"}
        or runtime.get("renderer") not in {"none", "webgl"}
        or not isinstance(runtime.get("target_devices"), list)
        or len(runtime["target_devices"]) != len(set(runtime["target_devices"]))
        or any(item not in {"desktop", "mobile"} for item in runtime["target_devices"])
    ):
        errors.append("scene runtime values are invalid")
    budget_names = {"status", "asset_bytes", "triangles", "draw_calls", "textures", "frame_p95_ms", "required_node_coverage_percent", "bbox_drift_percent"}
    budgets = scene.get("budgets")
    if not exact_keys(budgets, budget_names, {"status"}) or budgets.get("status") not in {"approved", "provisional"}:
        errors.append("scene budgets are malformed")
    else:
        for name, value in budgets.items():
            if name == "status" or value is None:
                continue
            if not is_number(value) or value < 0 or (name in {"asset_bytes", "triangles", "draw_calls", "textures"} and not isinstance(value, int)):
                errors.append(f"scene budget {name} is invalid")
        coverage = budgets.get("required_node_coverage_percent")
        if is_number(coverage) and coverage > 100:
            errors.append("scene required_node_coverage_percent exceeds 100")
    evidence = scene.get("required_evidence")
    if not isinstance(evidence, list) or len(evidence) != len(set(evidence)) or any(item not in KNOWN_EVIDENCE for item in evidence):
        errors.append("scene required_evidence is invalid")
    return errors


def run_contract_errors(run: Any) -> list[str]:
    required = {"schema", "run_id", "project_key", "created_at", "input_hashes", "route", "capabilities", "versions", "stages", "repairs", "evidence", "unverified"}
    if not exact_keys(run, required, required):
        return ["run contract keys do not match run.v1"]
    errors: list[str] = []
    if run.get("schema") != "3d-craft.run.v1" or not RUN_ID_PATTERN.fullmatch(str(run.get("run_id", ""))):
        errors.append("run schema or run_id is invalid")
    if not isinstance(run.get("project_key"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run["project_key"]):
        errors.append("run project_key is invalid")
    if not is_iso_datetime(run.get("created_at")):
        errors.append("run created_at must be a timezone-aware ISO date-time")
    input_hashes = run.get("input_hashes")
    if not isinstance(input_hashes, dict) or set(input_hashes) - {"scene_contract"} or any(not isinstance(value, str) or not HASH_PATTERN.fullmatch(value) for value in input_hashes.values()):
        errors.append("run input_hashes is invalid")
    capabilities = run.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) - CAPABILITIES or any(value not in {"available", "missing", "unverified"} for value in capabilities.values()):
        errors.append("run capabilities are invalid")
    versions = run.get("versions")
    if not isinstance(versions, dict) or not versions or any(not isinstance(key, str) or not key or not isinstance(value, str) or not value for key, value in versions.items()):
        errors.append("run versions are invalid")
    stages = run.get("stages")
    if not isinstance(stages, list) or any(
        not exact_keys(item, {"id", "status"}, {"id", "status"})
        or item.get("id") not in GATES
        or item.get("status") not in GATE_STATES
        for item in stages
    ):
        errors.append("run stages are invalid")
    elif len([item["id"] for item in stages]) != len(set(item["id"] for item in stages)):
        errors.append("run stage IDs must be unique")
    repairs = run.get("repairs")
    if not isinstance(repairs, list) or len(repairs) > 3 or any(
        not exact_keys(item, {"gate", "hypothesis", "change", "candidate_hash", "verdict"}, {"gate", "hypothesis", "change", "candidate_hash", "verdict"})
        or item.get("gate") not in GATES
        or not isinstance(item.get("hypothesis"), str) or not item["hypothesis"]
        or not isinstance(item.get("change"), str) or not item["change"]
        or not isinstance(item.get("candidate_hash"), str) or not HASH_PATTERN.fullmatch(item["candidate_hash"])
        or item.get("verdict") not in {"improved", "regressed", "unchanged"}
        for item in repairs
    ):
        errors.append("run repairs are invalid")
    evidence = run.get("evidence")
    if not isinstance(evidence, list) or any(
        not exact_keys(item, {"kind", "path"}, {"kind", "path"})
        or not isinstance(item.get("kind"), str) or not item["kind"]
        or not isinstance(item.get("path"), str) or not item["path"]
        for item in evidence
    ):
        errors.append("run evidence entries are invalid")
    unverified = run.get("unverified")
    if not isinstance(unverified, list) or any(not isinstance(item, str) or not item for item in unverified) or len(unverified) != len(set(unverified)):
        errors.append("run unverified entries are invalid")
    return errors


def asset_contract_errors(asset: Any) -> list[str]:
    required = {"schema", "authority", "source", "derived", "tool_versions", "licenses", "gltf_summary"}
    if not exact_keys(asset, required, required):
        return ["asset contract keys do not match asset.v1"]
    errors: list[str] = []
    if asset.get("schema") != "3d-craft.asset.v1" or asset.get("authority") not in AUTHORING_MODES:
        errors.append("asset schema or authority is invalid")

    def file_shape(entry: Any) -> bool:
        return bool(
            exact_keys(entry, {"path", "sha256", "bytes"}, {"path", "sha256", "bytes"})
            and isinstance(entry.get("path"), str) and entry["path"]
            and isinstance(entry.get("sha256"), str) and HASH_PATTERN.fullmatch(entry["sha256"])
            and isinstance(entry.get("bytes"), int) and not isinstance(entry["bytes"], bool) and entry["bytes"] >= 0
        )

    if not file_shape(asset.get("source")):
        errors.append("asset source entry is malformed")
    derived = asset.get("derived")
    if not isinstance(derived, list) or not derived or any(not file_shape(item) for item in derived):
        errors.append("asset derived entries are malformed")
    tool_versions = asset.get("tool_versions")
    if not isinstance(tool_versions, dict) or not tool_versions or any(not isinstance(key, str) or not key or not isinstance(value, str) or not value for key, value in tool_versions.items()):
        errors.append("asset tool_versions are malformed")
    licenses = asset.get("licenses")
    if not isinstance(licenses, list) or not licenses or any(
        not exact_keys(item, {"subject", "license", "source"}, {"subject", "license"})
        or not isinstance(item.get("subject"), str) or not item["subject"]
        or not isinstance(item.get("license"), str) or not item["license"]
        or ("source" in item and (not isinstance(item["source"], str) or not item["source"]))
        for item in licenses
    ):
        errors.append("asset licenses are malformed")
    summary = asset.get("gltf_summary")
    summary_keys = {"nodes", "meshes", "primitives", "materials", "textures", "animations", "triangles", "extensions"}
    if not exact_keys(summary, summary_keys, summary_keys):
        errors.append("asset gltf_summary is malformed")
    else:
        if any(not isinstance(summary[name], int) or isinstance(summary[name], bool) or summary[name] < 0 for name in summary_keys - {"extensions"}):
            errors.append("asset gltf_summary counts are invalid")
        if not isinstance(summary["extensions"], list) or any(not isinstance(item, str) or not item for item in summary["extensions"]) or len(summary["extensions"]) != len(set(summary["extensions"])):
            errors.append("asset gltf_summary extensions are invalid")
    return errors


def approved_budgets(scene: dict[str, Any] | None, names: tuple[str, ...]) -> dict[str, float] | None:
    budgets = (scene or {}).get("budgets")
    if not isinstance(budgets, dict) or budgets.get("status") != "approved":
        return None
    values: dict[str, float] = {}
    for name in names:
        value = budgets.get(name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            return None
        values[name] = float(value)
    return values


def required_evidence_for_route(expected: dict[str, Any], scene: dict[str, Any]) -> set[str]:
    required: set[str] = set()
    gates = set(expected["hard_gates"])
    if "reproduction" in gates:
        required.add("clean-reproduction")
    if "scene_integrity" in gates:
        required.add("blend-inspection")
    if "blender.render" in expected["required_capabilities"]:
        required.update((*FIXED_VIEWS, "contact-sheet", "lookdev", "visual-review"))
    if "gltf" in gates:
        required.add("gltf-validation")
    if "web_runtime" in gates or "cross_runtime" in gates:
        required.update(("browser-runtime", "browser-desktop-screenshot"))
        target_devices = as_object(scene.get("runtime")).get("target_devices")
        if isinstance(target_devices, list) and "mobile" in target_devices:
            required.add("browser-mobile-screenshot")
    return required


def gate(gate_id: str, status: str, evidence: list[str], note: str) -> dict[str, Any]:
    return {"id": gate_id, "status": status, "evidence": evidence, "note": note}


def manifest_file(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"manifest input is not a file: {resolved}")
    return {"path": str(resolved), "sha256": sha256_file(resolved), "bytes": resolved.stat().st_size}


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def observed_evidence(run_dir: Path) -> list[dict[str, str]]:
    evidence_names = {
        "blend-inspection.json": "blend-inspection",
        "render-evidence.json": "fixed-view-renders",
        "visual-review.json": "visual-review",
        "reproduction.json": "clean-reproduction",
        "gltf-validation.json": "gltf-validation",
        "browser-runtime.json": "browser-runtime",
        "host-smoke.json": "host-smoke",
    }
    return [
        {"kind": kind, "path": f"evidence/{name}"}
        for name, kind in evidence_names.items()
        if (run_dir / "evidence" / name).is_file()
    ]


def verified_entry_path(
    entry: Any,
    *,
    root: Path,
    require_bytes: bool = False,
) -> Path | None:
    if not verified_file_entry(entry, root=root, require_bytes=require_bytes):
        return None
    return Path(entry["path"]).expanduser().resolve()


def is_iso_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def visual_review_state(
    visual: dict[str, Any] | None,
    *,
    scene: dict[str, Any],
    blend_path: Path,
    render_path: Path,
) -> tuple[str, str]:
    if not visual:
        return "UNVERIFIED", "A candidate-bound visual review is missing."
    if visual.get("schema") != "3d-craft.visual-review.v1":
        return "FAIL", "Visual review has the wrong schema."
    candidate = as_object(visual.get("candidate"))
    if (
        not blend_path.is_file()
        or not render_path.is_file()
        or candidate.get("blend_sha256") != sha256_file(blend_path)
        or candidate.get("render_evidence_sha256") != sha256_file(render_path)
    ):
        return "FAIL", "Visual review is bound to a different blend or render-evidence report."
    rows = visual.get("features")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return "FAIL", "Visual review feature assessments are malformed."
    row_ids = [row.get("id") for row in rows]
    if any(not isinstance(row_id, str) or not row_id for row_id in row_ids):
        return "FAIL", "Visual review feature IDs are malformed."
    if len(row_ids) != len(set(row_ids)):
        return "FAIL", "Visual review contains duplicate feature assessments."
    by_id = {row.get("id"): row for row in rows}
    cameras = scene.get("cameras")
    allowed_views = set(cameras) if isinstance(cameras, list) else set()
    identity_features = scene.get("identity_features")
    scene_features = [feature for feature in identity_features if isinstance(feature, dict)] if isinstance(identity_features, list) else []
    expected_ids = {feature.get("id") for feature in scene_features}
    if set(row_ids) != expected_ids:
        return "FAIL", "Visual review feature assessments do not exactly match the scene contract."
    required_features = [
        feature
        for feature in scene_features
        if feature.get("importance") in {"critical", "major"}
    ]
    explicit_failure = False
    incomplete = False
    required_ids = {feature.get("id") for feature in required_features}
    for feature in scene_features:
        row = by_id.get(feature.get("id"))
        if not row or row.get("importance") != feature.get("importance"):
            return "FAIL", "Visual review feature importance does not match the scene contract."
        status = row.get("status")
        views = row.get("views")
        note = row.get("note")
        if (
            status not in {"PASS", "FAIL", "UNVERIFIED"}
            or not isinstance(views, list)
            or any(view not in allowed_views for view in views)
            or not isinstance(note, str)
            or (status in {"PASS", "FAIL"} and not note.strip())
        ):
            return "FAIL", "Visual review contains a malformed feature assessment."
        if status == "FAIL":
            explicit_failure = True
            continue
        if feature.get("id") in required_ids and (status != "PASS" or not views):
            incomplete = True
    if explicit_failure or visual.get("status") == "FAIL":
        return "FAIL", "At least one critical or major identity feature failed visual review."
    reviewer = as_object(visual.get("reviewer"))
    if (
        incomplete
        or visual.get("status") != "PASS"
        or reviewer.get("kind") not in {"agent", "human"}
        or not isinstance(reviewer.get("name"), str)
        or not reviewer.get("name", "").strip()
        or not is_iso_datetime(visual.get("reviewed_at"))
        or not isinstance(visual.get("overall_note"), str)
        or not visual.get("overall_note", "").strip()
    ):
        return "UNVERIFIED", "Visual review is incomplete or does not contain a traceable reviewer verdict."
    return "PASS", "Critical and major identity features passed a candidate-bound fixed-view review."


def bind_asset(args: argparse.Namespace) -> dict[str, Any]:
    """Create asset.json and bind scene/evidence inputs into an initialized run."""
    run_dir = Path(args.run_dir).expanduser()
    if not run_dir.is_absolute():
        raise ValueError("--run-dir must be absolute")
    run_dir = run_dir.resolve()
    run_path = run_dir / "run.json"
    scene_path = run_dir / "scene.json"
    asset_path = run_dir / "asset.json"
    if asset_path.exists():
        raise ValueError("asset.json already exists; create a new run for a new candidate")
    run = load_json(run_path)
    scene = load_json(scene_path)
    if not run or run.get("schema") != "3d-craft.run.v1":
        raise ValueError("run.json is missing or invalid; run init-run first")
    run_errors = run_contract_errors(run)
    if run_errors:
        raise ValueError("; ".join(run_errors))
    route = run.get("route")
    expected = expected_route(route)
    if not expected or route != expected:
        raise ValueError("run.route does not equal the deterministic route contract")
    if not scene or scene.get("schema") != "3d-craft.scene.v1":
        raise ValueError("scene.json is missing or has the wrong schema")
    contract_errors = scene_contract_errors(scene)
    if contract_errors:
        raise ValueError("; ".join(contract_errors))
    if scene.get("authoring_mode") != expected["authoring_mode"]:
        raise ValueError("scene authoring_mode differs from the route")
    if not args.license.strip() or not args.license_subject.strip():
        raise ValueError("--license and --license-subject must be non-empty")

    source = Path(args.source).expanduser()
    if not source.is_absolute():
        raise ValueError("--source must be absolute")
    source_entry = manifest_file(source)
    derived: list[dict[str, Any]] = []
    blend_path = run_dir / "assets" / "asset.blend"
    glb_path = run_dir / "assets" / "asset.glb"
    if expected["target"] in {"blender", "bridge"}:
        derived.append(manifest_file(blend_path))
    if expected["target"] in {"bridge", "web3d"}:
        derived.append(manifest_file(glb_path))

    gltf_summary = {
        "nodes": 0,
        "meshes": 0,
        "primitives": 0,
        "materials": 0,
        "textures": 0,
        "animations": 0,
        "triangles": 0,
        "extensions": [],
    }
    gltf_report = load_json(run_dir / "evidence" / "gltf-validation.json")
    if expected["target"] in {"bridge", "web3d"}:
        if not (
            gltf_report
            and gltf_report.get("schema") == "3d-craft.gltf-validation.v1"
            and gltf_report.get("status") == "PASS"
            and as_object(as_object(gltf_report.get("validator")).get("issues")).get("numErrors") == 0
            and report_file_binding(gltf_report, "asset", glb_path)
        ):
            raise ValueError("a passing, candidate-bound evidence/gltf-validation.json is required")
        semantic = as_object(gltf_report.get("semantic"))
        for name in gltf_summary:
            if name not in semantic:
                raise ValueError(f"gltf validation report is missing semantic.{name}")
            gltf_summary[name] = semantic[name]

    tool_versions = dict(run.get("versions", {}))
    blend_report = load_json(run_dir / "evidence" / "blend-inspection.json")
    if isinstance((blend_report or {}).get("blender_version"), str):
        tool_versions["blender"] = blend_report["blender_version"]
    validator_version = as_object((gltf_report or {}).get("validator")).get("validatorVersion")
    if isinstance(validator_version, str):
        tool_versions["gltf-validator"] = validator_version
    license_entry = {"subject": args.license_subject, "license": args.license}
    if args.license_source:
        license_entry["source"] = args.license_source
    asset = {
        "schema": "3d-craft.asset.v1",
        "authority": expected["authoring_mode"],
        "source": source_entry,
        "derived": derived,
        "tool_versions": tool_versions,
        "licenses": [license_entry],
        "gltf_summary": gltf_summary,
    }

    if not isinstance(run.get("input_hashes"), dict):
        run["input_hashes"] = {}
    run["input_hashes"]["scene_contract"] = sha256_file(scene_path)
    run["evidence"] = observed_evidence(run_dir)
    write_json_atomic(asset_path, asset)
    write_json_atomic(run_path, run)
    return {
        "schema": "3d-craft.bind-asset.v1",
        "command": "bind-asset",
        "status": "pass",
        "run_dir": str(run_dir),
        "scene_sha256": run["input_hashes"]["scene_contract"],
        "asset_manifest": str(run_dir / "asset.json"),
        "source": source_entry,
        "derived": derived,
    }


def init_visual_review(args: argparse.Namespace) -> dict[str, Any]:
    """Create a candidate-bound visual assessment template without claiming a verdict."""
    run_dir = Path(args.run_dir).expanduser()
    if not run_dir.is_absolute():
        raise ValueError("--run-dir must be absolute")
    run_dir = run_dir.resolve()
    run_path = run_dir / "run.json"
    scene_path = run_dir / "scene.json"
    blend_path = run_dir / "assets" / "asset.blend"
    render_path = run_dir / "evidence" / "render-evidence.json"
    review_path = run_dir / "evidence" / "visual-review.json"
    if review_path.exists():
        raise ValueError("visual-review.json already exists; refusing to overwrite an assessment")
    run = load_json(run_path)
    scene = load_json(scene_path)
    renders = load_json(render_path)
    expected = expected_route((run or {}).get("route"))
    if not run or run.get("schema") != "3d-craft.run.v1" or not expected:
        raise ValueError("run.json is missing or does not contain a deterministic route")
    run_errors = run_contract_errors(run)
    if run_errors:
        raise ValueError("; ".join(run_errors))
    if "blender.render" not in expected["required_capabilities"]:
        raise ValueError("the routed evidence level does not require a visual review")
    if not scene or scene.get("schema") != "3d-craft.scene.v1":
        raise ValueError("scene.json is missing or has the wrong schema")
    contract_errors = scene_contract_errors(scene)
    if contract_errors:
        raise ValueError("; ".join(contract_errors))
    if not (
        renders
        and renders.get("schema") == "3d-craft.render-evidence.v1"
        and renders.get("status") == "PASS"
        and report_file_binding(renders, "blend", blend_path)
        and report_file_binding(renders, "scene_contract", scene_path)
    ):
        raise ValueError("a passing, candidate- and scene-bound render-evidence.json is required")
    reviewer_kind = args.reviewer_kind
    review = {
        "schema": "3d-craft.visual-review.v1",
        "status": "UNVERIFIED",
        "candidate": {
            "blend_sha256": sha256_file(blend_path),
            "render_evidence_sha256": sha256_file(render_path),
        },
        "reviewer": {"kind": reviewer_kind, "name": args.reviewer_name or ""},
        "reviewed_at": None,
        "features": [
            {
                "id": feature.get("id"),
                "importance": feature.get("importance"),
                "status": "UNVERIFIED",
                "views": [],
                "note": "",
            }
            for feature in scene.get("identity_features", [])
            if isinstance(feature, dict)
        ],
        "overall_note": "",
    }
    write_json_atomic(review_path, review)
    run["evidence"] = observed_evidence(run_dir)
    write_json_atomic(run_path, run)
    return {
        "schema": "3d-craft.init-visual-review.v1",
        "command": "init-visual-review",
        "status": "pass",
        "review_file": str(review_path),
        "features": len(review["features"]),
        "next": "Inspect the bound fixed views, then fill reviewer, reviewed_at, feature verdicts/views/notes, overall_note, and status.",
    }


def validate_run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    run_dir = Path(args.run_dir).expanduser()
    if not run_dir.is_absolute():
        raise ValueError("--run-dir must be absolute")
    run_dir = run_dir.resolve()
    skill_root = Path(__file__).resolve().parent.parent
    run = load_json(run_dir / "run.json")
    scene = load_json(run_dir / "scene.json")
    asset = load_json(run_dir / "asset.json")
    blend = load_json(run_dir / "evidence" / "blend-inspection.json")
    renders = load_json(run_dir / "evidence" / "render-evidence.json")
    visual = load_json(run_dir / "evidence" / "visual-review.json")
    reproduction = load_json(run_dir / "evidence" / "reproduction.json")
    gltf = load_json(run_dir / "evidence" / "gltf-validation.json")
    browser = load_json(run_dir / "evidence" / "browser-runtime.json")
    host_smoke = load_json(run_dir / "evidence" / "host-smoke.json")
    gate_results: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, str]] = []
    run_object = run or {}
    scene_object = scene or {}
    asset_object = asset or {}
    route = run_object.get("route")
    expected = expected_route(route)
    route_ok = bool(expected and route == expected)
    required_gates = expected["hard_gates"] if expected else ["authority", "delivery"]
    required_capabilities = expected["required_capabilities"] if expected else []
    target = expected.get("target") if expected else None
    render_required = "blender.render" in required_capabilities

    asset_blend = run_dir / "assets" / "asset.blend"
    asset_glb = run_dir / "assets" / "asset.glb"
    blend_entry = declared_file(asset, asset_blend)
    glb_entry = declared_file(asset, asset_glb)
    blend_declared_ok = verified_file_entry(blend_entry, expected_path=asset_blend, root=run_dir / "assets", require_bytes=True)
    glb_declared_ok = verified_file_entry(glb_entry, expected_path=asset_glb, root=run_dir / "assets", require_bytes=True)
    blend_hash = sha256_file(asset_blend) if asset_blend.is_file() else None
    glb_hash = sha256_file(asset_glb) if asset_glb.is_file() else None

    authority_errors: list[str] = []
    authority_errors.extend(run_contract_errors(run))
    if not route_ok:
        authority_errors.append("run.route does not equal the deterministic route contract")
    authority_errors.extend(scene_contract_errors(scene))
    authority_errors.extend(asset_contract_errors(asset))
    if expected and (scene or {}).get("authoring_mode") != expected["authoring_mode"]:
        authority_errors.append("scene authoring_mode differs from the route")
    if expected and (asset or {}).get("authority") != expected["authoring_mode"]:
        authority_errors.append("asset authority differs from the route")
    if expected and scene:
        required_evidence = scene.get("required_evidence")
        routed_evidence = required_evidence_for_route(expected, scene)
        if (
            not isinstance(required_evidence, list)
            or any(not isinstance(item, str) or item not in KNOWN_EVIDENCE for item in required_evidence)
            or set(required_evidence) != routed_evidence
        ):
            authority_errors.append("scene.required_evidence does not exactly match the routed evidence contract")
        runtime = as_object(scene.get("runtime"))
        if target == "blender" and runtime != {"engine": "none", "renderer": "none", "target_devices": []}:
            authority_errors.append("Blender-only routes require runtime engine/renderer none and no target devices")
        if target in {"bridge", "web3d"} and (
            runtime.get("engine") not in {"three", "r3f"}
            or runtime.get("renderer") != "webgl"
            or not runtime.get("target_devices")
        ):
            authority_errors.append("Bridge/Web3D routes require a Three.js or R3F WebGL runtime and target devices")
    scene_hash = sha256_file(run_dir / "scene.json") if (run_dir / "scene.json").is_file() else None
    if as_object(run_object.get("input_hashes")).get("scene_contract") != scene_hash:
        authority_errors.append("run.input_hashes.scene_contract does not bind scene.json")
    if not verified_file_entry(asset_object.get("source"), require_bytes=True):
        authority_errors.append("asset source path, byte count, or SHA-256 is invalid")
    licenses = asset_object.get("licenses")
    if not isinstance(licenses, list) or not licenses or any(
        not isinstance(item, dict)
        or not isinstance(item.get("subject"), str)
        or not item.get("subject", "").strip()
        or not isinstance(item.get("license"), str)
        or not item.get("license", "").strip()
        for item in licenses
    ):
        authority_errors.append("asset licenses are missing or incomplete")
    tool_versions = asset_object.get("tool_versions")
    if not isinstance(tool_versions, dict) or not tool_versions or any(
        not isinstance(value, str) or not value.strip() for value in tool_versions.values()
    ):
        authority_errors.append("asset tool_versions are missing or incomplete")
    if target in {"blender", "bridge"} and not blend_declared_ok:
        authority_errors.append("asset.blend is missing or differs from asset.json")
    if target in {"bridge", "web3d"} and not glb_declared_ok:
        authority_errors.append("asset.glb is missing or differs from asset.json")
    run_capabilities = as_object(run_object.get("capabilities"))
    if expected and any(run_capabilities.get(name) not in {"available", "missing", "unverified"} for name in required_capabilities):
        authority_errors.append("run.capabilities does not declare every routed capability")
    run_stages = run_object.get("stages")
    if expected and (
        not isinstance(run_stages, list)
        or [item.get("id") for item in run_stages if isinstance(item, dict)] != required_gates
    ):
        authority_errors.append("run.stages does not match the routed hard gates")
    if not isinstance(run_object.get("repairs"), list) or len(run_object.get("repairs", [])) > 3:
        authority_errors.append("run.repairs is invalid or exceeds the three-attempt limit")
    authority_ok = not authority_errors
    authority_note = "Authority contracts and file hashes are internally consistent." if authority_ok else "; ".join(authority_errors) + "."
    gate_results["authority"] = gate("authority", "PASS" if authority_ok else "FAIL", ["run.json", "scene.json", "asset.json"] if authority_ok else [], authority_note)
    if not authority_ok:
        issues.append({"severity": "P0", "gate": "authority", "message": authority_note})

    reproduction_ok = False
    if "reproduction" in required_gates:
        reproduction_candidate = as_object((reproduction or {}).get("candidate"))
        reproduction_binding_ok = bool(
            (target not in {"blender", "bridge"} or reproduction_candidate.get("blend_sha256") == blend_hash)
            and (target != "bridge" or reproduction_candidate.get("gltf_sha256") == glb_hash)
        )
        reproduction_ok = bool(
            reproduction
            and reproduction.get("schema") == "3d-craft.reproduction.v1"
            and reproduction.get("match") is True
            and reproduction_binding_ok
        )
        reproduction_status = "PASS" if reproduction_ok else ("FAIL" if reproduction else "UNVERIFIED")
        gate_results["reproduction"] = gate(
            "reproduction",
            reproduction_status,
            ["evidence/reproduction.json"] if reproduction else [],
            "Two normalized builds match and the report is bound to the candidate." if reproduction_ok else "Clean reproduction is missing, mismatched, or not bound to the candidate.",
        )

    blend_report_ok = bool(
        blend
        and blend.get("schema") == "3d-craft.blend-inspection.v1"
        and blend.get("status") == "PASS"
        and report_file_binding(blend, "blend", asset_blend)
    )
    if "scene_integrity" in required_gates:
        scene_status = "PASS" if blend_report_ok else ("FAIL" if blend else "UNVERIFIED")
        gate_results["scene_integrity"] = gate(
            "scene_integrity",
            scene_status,
            ["evidence/blend-inspection.json"] if blend else [],
            "Blender inspection passed and is bound to asset.blend." if blend_report_ok else "Blender scene inspection is missing, failing, or bound to another file.",
        )

    render_artifact_paths: list[Path] = []
    render_evidence_ok = False
    if "identity" in required_gates:
        coverage_ok = bool(
            blend_report_ok
            and as_object(blend.get("coverage")).get("components_percent") == 100
            and as_object(blend.get("coverage")).get("materials_percent") == 100
        )
        required_views = set(FIXED_VIEWS)
        rendered_views = set()
        render_views = (renders or {}).get("views")
        for item in render_views if isinstance(render_views, list) else []:
            artifact = verified_entry_path(item, root=run_dir / "evidence")
            if artifact:
                rendered_views.add(item.get("view"))
                render_artifact_paths.append(artifact)
        contact_sheet_path = verified_entry_path((renders or {}).get("contact_sheet"), root=run_dir / "evidence")
        lookdev_path = verified_entry_path((renders or {}).get("lookdev"), root=run_dir / "evidence")
        if contact_sheet_path:
            render_artifact_paths.append(contact_sheet_path)
        if lookdev_path:
            render_artifact_paths.append(lookdev_path)
        render_evidence_ok = bool(
            renders
            and renders.get("schema") == "3d-craft.render-evidence.v1"
            and renders.get("status") == "PASS"
            and report_file_binding(renders, "blend", asset_blend)
            and report_file_binding(renders, "scene_contract", run_dir / "scene.json")
            and required_views <= rendered_views
            and contact_sheet_path
            and lookdev_path
        )
        if not render_required:
            review_status, review_note = "UNVERIFIED", "Static evidence cannot prove silhouette or key visual features."
        else:
            review_status, review_note = visual_review_state(
                visual,
                scene=scene or {},
                blend_path=asset_blend,
                render_path=run_dir / "evidence" / "render-evidence.json",
            )
        if not blend:
            identity_status = "UNVERIFIED"
            identity_note = "Blender identity inspection is missing."
        elif not coverage_ok:
            identity_status = "FAIL"
            identity_note = "Required component or material coverage failed."
        elif not render_required:
            identity_status = "UNVERIFIED"
            identity_note = review_note
        elif not renders:
            identity_status = "UNVERIFIED"
            identity_note = "Fixed-view render evidence is missing."
        elif not render_evidence_ok:
            identity_status = "FAIL"
            identity_note = "Fixed-view render evidence is invalid or bound to another asset."
        else:
            identity_status = review_status
            identity_note = review_note
        identity_evidence = []
        if blend:
            identity_evidence.append("evidence/blend-inspection.json")
        if renders and render_required:
            identity_evidence.append("evidence/render-evidence.json")
        if visual and render_required:
            identity_evidence.append("evidence/visual-review.json")
        gate_results["identity"] = gate("identity", identity_status, identity_evidence, identity_note)

    gltf_core_ok = False
    if "gltf" in required_gates:
        gltf_summary = as_object((gltf or {}).get("semantic"))
        declared_summary = as_object(asset_object.get("gltf_summary"))
        summary_keys = ("nodes", "meshes", "primitives", "materials", "textures", "animations", "triangles", "extensions")
        actual_extensions = gltf_summary.get("extensions")
        declared_extensions = declared_summary.get("extensions")
        semantic_match = bool(
            isinstance(actual_extensions, list)
            and isinstance(declared_extensions, list)
            and sorted(actual_extensions) == sorted(declared_extensions)
            and all(gltf_summary.get(name) == declared_summary.get(name) for name in summary_keys if name != "extensions")
        )
        gltf_core_ok = bool(
            gltf
            and gltf.get("schema") == "3d-craft.gltf-validation.v1"
            and gltf.get("status") == "PASS"
            and as_object(as_object(gltf.get("validator")).get("issues")).get("numErrors") == 0
            and report_file_binding(gltf, "asset", asset_glb)
            and semantic_match
        )
        gltf_budgets = approved_budgets(scene, ("asset_bytes", "triangles"))
        gltf_bytes = gltf_summary.get("bytes")
        gltf_triangles = gltf_summary.get("triangles")
        gltf_budget_ok = bool(
            gltf_budgets
            and is_number(gltf_bytes)
            and is_number(gltf_triangles)
            and gltf_bytes <= gltf_budgets["asset_bytes"]
            and gltf_triangles <= gltf_budgets["triangles"]
        )
        if gltf_core_ok and gltf_budget_ok:
            gltf_status = "PASS"
        elif not gltf:
            gltf_status = "UNVERIFIED"
        elif gltf_core_ok and gltf_budgets is None:
            gltf_status = "UNVERIFIED"
        else:
            gltf_status = "FAIL"
        gltf_note = "Khronos validation, semantic manifest, candidate binding, and approved asset budgets passed."
        if gltf_status != "PASS":
            gltf_note = "GLB validity, semantic identity, candidate binding, or approved asset budgets are missing or failing."
        gate_results["gltf"] = gate("gltf", gltf_status, ["evidence/gltf-validation.json"] if gltf else [], gltf_note)

    browser_asset_ok = bool(browser and glb_hash and as_object(browser.get("asset")).get("sha256") == glb_hash)
    browser_blocked = bool(browser and browser.get("status") == "BLOCKED")
    browser_page_ready = bool(browser and (browser.get("status") == "ready" or browser.get("page_status") == "ready"))
    browser_base_ok = bool(
        browser
        and browser.get("schema") == "3d-craft.browser-runtime.v1"
        and browser.get("runtime") == "browser67"
        and browser_page_ready
        and browser_asset_ok
    )
    desktop_screenshot = (browser or {}).get("desktop_screenshot")
    desktop_screenshot_path = verified_entry_path(
        desktop_screenshot,
        root=run_dir / "evidence",
        require_bytes=True,
    )
    desktop_screenshot_ok = bool(
        desktop_screenshot_path
        and desktop_screenshot.get("visual_review") == "PASS"
    )
    browser_artifact_paths: list[Path] = [desktop_screenshot_path] if desktop_screenshot_path else []
    cross_budgets = approved_budgets(scene, ("required_node_coverage_percent", "bbox_drift_percent"))
    if "cross_runtime" in required_gates:
        cross_metrics = as_object((browser or {}).get("cross_runtime"))
        cross_core_ok = bool(
            browser
            and browser.get("schema") == "3d-craft.browser-runtime.v1"
            and browser.get("runtime") == "browser67"
            and browser_asset_ok
            and desktop_screenshot_ok
        )
        node_coverage = cross_metrics.get("required_node_coverage_percent")
        bbox_drift = cross_metrics.get("bbox_drift_percent")
        cross_budget_ok = bool(
            cross_budgets
            and is_number(node_coverage)
            and is_number(bbox_drift)
            and node_coverage >= cross_budgets["required_node_coverage_percent"]
            and bbox_drift <= cross_budgets["bbox_drift_percent"]
        )
        if browser_blocked:
            cross_status = "BLOCKED"
        elif cross_core_ok and cross_budget_ok:
            cross_status = "PASS"
        elif not browser:
            cross_status = "UNVERIFIED"
        elif cross_core_ok and cross_budgets is None:
            cross_status = "UNVERIFIED"
        else:
            cross_status = "FAIL"
        cross_note = "Browser and GLB identity passed approved parity budgets."
        if cross_status == "BLOCKED":
            cross_note = f"Browser evidence is blocked: {browser.get('blocker', 'unspecified prerequisite')}."
        elif cross_status != "PASS":
            cross_note = "Cross-runtime identity, screenshot evidence, candidate binding, or approved parity budgets are missing or failing."
        gate_results["cross_runtime"] = gate(
            "cross_runtime",
            cross_status,
            ["evidence/browser-runtime.json"] if browser else [],
            cross_note,
        )

    if "web_runtime" in required_gates:
        web_metrics = as_object((browser or {}).get("metrics"))
        web_budgets = approved_budgets(scene, ("draw_calls", "textures", "frame_p95_ms"))
        lifecycle = as_object((browser or {}).get("lifecycle"))
        target_devices_value = as_object(scene_object.get("runtime")).get("target_devices")
        target_devices = target_devices_value if isinstance(target_devices_value, list) else []
        mobile_required = "mobile" in target_devices
        mobile_screenshot = (browser or {}).get("mobile_screenshot")
        mobile_screenshot_path = verified_entry_path(
            mobile_screenshot,
            root=run_dir / "evidence",
            require_bytes=True,
        )
        mobile_screenshot_ok = bool(
            mobile_screenshot_path
            and mobile_screenshot.get("visual_review") == "PASS"
        )
        if mobile_screenshot_path:
            browser_artifact_paths.append(mobile_screenshot_path)
        mobile_ok = bool(
            not mobile_required
            or (
                as_object((browser or {}).get("responsive_layout")).get("status") == "PASS"
                and as_object((browser or {}).get("responsive_layout")).get("horizontal_overflow") is False
                and mobile_screenshot_ok
            )
        )
        web_core_ok = bool(
            browser
            and browser.get("schema") == "3d-craft.browser-runtime.v1"
            and browser.get("runtime") == "browser67"
            and browser.get("status") == "ready"
            and browser.get("console_errors") == 0
            and browser_asset_ok
            and as_object(browser.get("network")).get("status") == "PASS"
            and is_number(as_object(browser.get("raf")).get("delta"))
            and as_object(browser.get("raf")).get("delta") > 0
            and lifecycle.get("remount_test_status") == "PASS"
            and lifecycle.get("ready_after_clean_reload") is True
            and mobile_ok
        )
        draw_calls = web_metrics.get("draw_calls")
        texture_count = web_metrics.get("textures")
        frame_p95_ms = web_metrics.get("frame_p95_ms")
        web_budget_ok = bool(
            web_budgets
            and is_number(draw_calls)
            and is_number(texture_count)
            and is_number(frame_p95_ms)
            and draw_calls <= web_budgets["draw_calls"]
            and texture_count <= web_budgets["textures"]
            and frame_p95_ms <= web_budgets["frame_p95_ms"]
        )
        if browser_blocked:
            web_status = "BLOCKED"
        elif web_core_ok and web_budget_ok:
            web_status = "PASS"
        elif not browser:
            web_status = "UNVERIFIED"
        elif web_core_ok and web_budgets is None:
            web_status = "UNVERIFIED"
        else:
            web_status = "FAIL"
        web_note = "browser67 runtime, lifecycle, responsive evidence, and approved desktop budgets passed."
        if web_status == "BLOCKED":
            web_note = f"Browser evidence is blocked: {browser.get('blocker', 'unspecified prerequisite')}."
        elif web_status != "PASS":
            web_note = "Browser runtime, lifecycle, responsive evidence, candidate binding, or approved budgets are missing or failing."
        gate_results["web_runtime"] = gate(
            "web_runtime",
            web_status,
            ["evidence/browser-runtime.json"] if browser else [],
            web_note,
        )

    core_delivery_files = [run_dir / "run.json", run_dir / "scene.json", run_dir / "asset.json"]
    if target in {"blender", "bridge"}:
        core_delivery_files.append(asset_blend)
    if target in {"bridge", "web3d"}:
        core_delivery_files.append(asset_glb)
    evidence_by_gate = {
        "reproduction": run_dir / "evidence" / "reproduction.json",
        "scene_integrity": run_dir / "evidence" / "blend-inspection.json",
        "gltf": run_dir / "evidence" / "gltf-validation.json",
        "cross_runtime": run_dir / "evidence" / "browser-runtime.json",
        "web_runtime": run_dir / "evidence" / "browser-runtime.json",
    }
    required_evidence_files = {
        path for gate_id, path in evidence_by_gate.items() if gate_id in required_gates
    }
    if render_required:
        required_evidence_files.add(run_dir / "evidence" / "render-evidence.json")
        required_evidence_files.add(run_dir / "evidence" / "visual-review.json")
    evidence_artifacts = sorted(set([*render_artifact_paths, *browser_artifact_paths]))
    delivery_files = [*core_delivery_files, *sorted(required_evidence_files), *evidence_artifacts]
    upstream_gates = [gate_results[gate_id] for gate_id in required_gates if gate_id != "delivery" and gate_id in gate_results]
    upstream_complete = len(upstream_gates) == len([gate_id for gate_id in required_gates if gate_id != "delivery"])
    files_complete = all(path.is_file() for path in delivery_files)
    if not route_ok or not upstream_complete or any(item["status"] == "FAIL" for item in upstream_gates):
        delivery_status = "FAIL"
    elif any(item["status"] == "BLOCKED" for item in upstream_gates):
        delivery_status = "BLOCKED"
    elif not files_complete or any(item["status"] == "UNVERIFIED" for item in upstream_gates):
        delivery_status = "UNVERIFIED"
    else:
        delivery_status = "PASS"
    delivery_evidence = [
        str(path.relative_to(run_dir))
        for path in delivery_files
        if path.is_file() and path_is_within(path, run_dir)
    ]
    gate_results["delivery"] = gate(
        "delivery",
        delivery_status,
        delivery_evidence,
        "The routed delivery set, evidence artifacts, and all upstream hard gates passed."
        if delivery_status == "PASS"
        else "The routed delivery set is incomplete, unverified, blocked, or an upstream hard gate failed.",
    )

    if run and route_ok and not run_contract_errors(run):
        evidenced_capabilities: set[str] = set()
        if blend_report_ok:
            evidenced_capabilities.update(("blender.version", "blender.inspect"))
        if reproduction_ok and target in {"blender", "bridge"} and expected["intent"] in {"build", "repair"}:
            evidenced_capabilities.add("blender.execute")
        if render_evidence_ok:
            evidenced_capabilities.add("blender.render")
        if reproduction_ok and gltf_core_ok and target == "bridge":
            evidenced_capabilities.add("blender.export")
        if gltf_core_ok:
            evidenced_capabilities.update(("asset.gltf.validate", "asset.gltf.inspect"))
        if browser_base_ok:
            evidenced_capabilities.add("browser.navigate")
        if browser_base_ok and isinstance(browser.get("console_errors"), int):
            evidenced_capabilities.add("browser.console.read")
        if browser_base_ok and as_object(browser.get("network")).get("status") in {"PASS", "FAIL"}:
            evidenced_capabilities.add("browser.network.read")
        if browser_base_ok and all(name in as_object(browser.get("metrics")) for name in ("draw_calls", "textures", "frame_p95_ms")):
            evidenced_capabilities.add("browser.performance.profile")
        if browser_base_ok and desktop_screenshot_ok:
            evidenced_capabilities.add("browser.capture")
        for capability in required_capabilities:
            prior = run["capabilities"].get(capability)
            run["capabilities"][capability] = (
                "available" if capability in evidenced_capabilities else "missing" if prior == "missing" else "unverified"
            )
        run["unverified"] = [
            capability
            for capability in required_capabilities
            if run["capabilities"].get(capability) != "available"
        ]
        run["stages"] = [
            {"id": gate_id, "status": gate_results[gate_id]["status"].lower()}
            for gate_id in required_gates
            if gate_id in gate_results
        ]
        run["evidence"] = observed_evidence(run_dir)
        write_json_atomic(run_dir / "run.json", run)

    gates = [gate_results[gate_id] for gate_id in GATES if gate_id in required_gates and gate_id in gate_results]
    for item in gates:
        if item["status"] == "FAIL" and not any(issue.get("gate") == item["id"] for issue in issues):
            issues.append({"severity": "P1", "gate": item["id"], "message": item["note"]})
        elif item["status"] == "BLOCKED":
            issues.append({"severity": "P1", "gate": item["id"], "message": item["note"]})
        elif item["status"] == "UNVERIFIED":
            issues.append({"severity": "P2", "gate": item["id"], "message": item["note"]})
    optional_unverified = list(
        dict.fromkeys(
            [
                *(run_object.get("unverified") if isinstance(run_object.get("unverified"), list) else []),
                *((browser or {}).get("unverified") if isinstance((browser or {}).get("unverified"), list) else []),
            ]
        )
    )
    browser_warnings = (browser or {}).get("warnings")
    for warning in browser_warnings if isinstance(browser_warnings, list) else []:
        issues.append({"severity": "P2", "gate": "web_runtime", "message": str(warning)})
    host_smoke_current = bool(
        host_smoke
        and host_smoke.get("status") == "PASS"
        and host_smoke.get("candidate_tree_sha256") == tree_sha256(skill_root)
    )
    if host_smoke and not host_smoke_current:
        issues.append({"severity": "P2", "gate": "delivery", "message": "Optional host smoke targets a different Skill tree and was not credited."})
    overall = max((item["status"] for item in gates), key=lambda status: STATUS_RANK[status])
    source_value = as_object(asset_object.get("source")).get("path")
    source_path = Path(source_value if isinstance(source_value, str) and source_value else "<declared-source>")
    commands = []
    if expected and expected["intent"] in {"build", "repair"} and expected["authoring_mode"] == "procedural":
        commands.append(" ".join(
            shlex.quote(part)
            for part in [
                "blender",
                "--background",
                "--factory-startup",
                "--python-exit-code",
                "2",
                "--python",
                str(source_path),
                "--",
                "--output-dir",
                str(run_dir / "assets"),
            ]
        ))
    if target in {"blender", "bridge"}:
        commands.append(" ".join(
            shlex.quote(part)
            for part in [
                "blender",
                "--background",
                str(run_dir / "assets" / "asset.blend"),
                "--python-exit-code",
                "2",
                "--python",
                str(skill_root / "scripts" / "blend_inspect.py"),
                "--",
                "--scene-contract",
                str(run_dir / "scene.json"),
                "--output",
                str(run_dir / "evidence" / "blend-inspection.json"),
            ]
        ))
    if render_required:
        commands.append(" ".join(
            shlex.quote(part)
            for part in [
                "blender",
                "--background",
                str(run_dir / "assets" / "asset.blend"),
                "--python-exit-code",
                "2",
                "--python",
                str(skill_root / "scripts" / "render_evidence.py"),
                "--",
                "--scene-contract",
                str(run_dir / "scene.json"),
                "--output-dir",
                str(run_dir / "evidence"),
            ]
        ))
    if target in {"bridge", "web3d"}:
        commands.append(" ".join(
            shlex.quote(part)
            for part in [
                "node",
                str(skill_root / "scripts" / "gltf_validate.mjs"),
                str(run_dir / "assets" / "asset.glb"),
                "--output",
                str(run_dir / "evidence" / "gltf-validation.json"),
            ]
        ))
    commands.append(" ".join(
            shlex.quote(part)
            for part in [
                "python3",
                str(skill_root / "scripts" / "3d_craft.py"),
                "validate",
                "--run-dir",
                str(run_dir),
                "--json",
            ]
        ))
    candidate_path = asset_glb if target in {"bridge", "web3d"} else asset_blend
    candidate_hash = sha256_file(candidate_path) if candidate_path.is_file() else "0" * 64
    report = {
        "schema": "3d-craft.validation.v1",
        "command": "validate",
        "candidate_sha256": candidate_hash,
        "status": overall,
        "gates": gates,
        "evidence": sorted(
            {
                *{evidence for item in gates for evidence in item["evidence"]},
                *({"evidence/host-smoke.json"} if host_smoke_current else set()),
            }
        ),
        "issues": issues,
        "repairs": run_object.get("repairs") if isinstance(run_object.get("repairs"), list) else [],
        "delivery": {
            "files": [{"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in delivery_files if path.is_file()],
            "commands": commands,
            "unverified": list(dict.fromkeys([
                *[item["id"] for item in gates if item["status"] != "PASS"],
                *optional_unverified,
            ])),
        },
    }
    report_path = run_dir / "reports" / "validation.json"
    write_json_atomic(report_path, {k: v for k, v in report.items() if k != "command"})
    return report, 0 if overall == "PASS" else 2


def add_route_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", choices=TARGETS, default="bridge")
    parser.add_argument("--intent", choices=INTENTS, default="build")
    parser.add_argument("--profile", choices=PROFILES, default="product-asset")
    parser.add_argument("--quality-tier", choices=QUALITY_TIERS, default="production")
    parser.add_argument("--authoring-mode", choices=AUTHORING_MODES, default="hybrid")
    parser.add_argument("--evidence-level", choices=EVIDENCE_LEVELS, default="assured")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="3D-Craft deterministic CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="Inspect local V0.1 capabilities")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--output")
    route = subparsers.add_parser("route", help="Resolve a supported V0.1 route")
    add_route_arguments(route)
    route.add_argument("--json", action="store_true")
    route.add_argument("--output")
    init = subparsers.add_parser("init-run", help="Create an external run directory and run.json")
    init.add_argument("--project-key", required=True)
    init.add_argument("--run-id")
    init.add_argument("--run-dir")
    add_route_arguments(init)
    init.add_argument("--json", action="store_true")
    init.add_argument("--output")
    bind = subparsers.add_parser("bind-asset", help="Bind scene, source, derived assets, license, and GLB semantics")
    bind.add_argument("--run-dir", required=True)
    bind.add_argument("--source", required=True)
    bind.add_argument("--license", required=True)
    bind.add_argument("--license-subject", required=True)
    bind.add_argument("--license-source")
    bind.add_argument("--json", action="store_true")
    visual = subparsers.add_parser("init-visual-review", help="Create a candidate-bound fixed-view assessment template")
    visual.add_argument("--run-dir", required=True)
    visual.add_argument("--reviewer-kind", choices=("agent", "human"), default="agent")
    visual.add_argument("--reviewer-name")
    visual.add_argument("--json", action="store_true")
    validate = subparsers.add_parser("validate", help="Aggregate run evidence into hard gates")
    validate.add_argument("--run-dir", required=True)
    validate.add_argument("--json", action="store_true")
    validate.add_argument("--output")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            payload, exit_code = doctor_payload(), 0
        elif args.command == "route":
            payload, exit_code = build_route(args), 0
        elif args.command == "init-run":
            payload, exit_code = init_run(args), 0
        elif args.command == "bind-asset":
            payload, exit_code = bind_asset(args), 0
        elif args.command == "init-visual-review":
            payload, exit_code = init_visual_review(args), 0
        else:
            payload, exit_code = validate_run(args)
        emit(payload, as_json=args.json, output=getattr(args, "output", None))
        return exit_code
    except (OSError, ValueError) as error:
        print(f"3d-craft: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
