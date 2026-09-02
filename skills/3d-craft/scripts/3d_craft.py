#!/usr/bin/env python3
"""Portable route, doctor, run initialization, and validation CLI for 3D-Craft."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
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


def build_route(args: argparse.Namespace) -> dict[str, Any]:
    refs = ["authority-and-evidence.md", "repair-and-security.md"]
    capabilities: list[str] = []
    gates = ["authority", "delivery"]
    if args.target in {"blender", "bridge"}:
        refs.append("blender-production.md")
        capabilities.extend(["blender.version", "blender.inspect", "blender.execute"])
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
    capabilities = {
        "blender.version": "available" if blender_ok else "unverified",
        "blender.inspect": "available" if blender_ok else "unverified",
        "blender.execute": "available" if blender_ok else "unverified",
        "blender.render": "available" if blender_ok else "unverified",
        "blender.export": "available" if blender_ok else "unverified",
        "asset.gltf.validate": "available" if node_ok else "unverified",
        "asset.gltf.inspect": "available" if node_ok else "unverified",
        "browser.capture": "unverified",
        "browser.console.read": "unverified",
        "browser.performance.profile": "unverified",
    }
    problems = []
    if not blender_ok:
        problems.append("Blender 5.2.1 LTS was not observed on PATH.")
    if not node_ok:
        problems.append("Node.js 22.12 or newer was not observed on PATH.")
    return {
        "schema": "3d-craft.doctor.v1",
        "command": "doctor",
        "status": "pass" if not problems else "partial",
        "skill_version": SKILL_VERSION,
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "tools": {"python": python, "node": node, "npm": npm, "blender": blender},
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
    if args.run_dir:
        run_dir = Path(args.run_dir).expanduser()
        if not run_dir.is_absolute():
            raise ValueError("--run-dir must be absolute")
        run_dir = run_dir.resolve()
    else:
        run_dir = default_run_root() / args.project_key / run_id
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


def verified_file_entry(entry: Any) -> bool:
    """Verify one evidence-manifest file entry without trusting a claimed hash."""
    if not isinstance(entry, dict):
        return False
    raw_path = entry.get("path")
    claimed_hash = entry.get("sha256")
    if not isinstance(raw_path, str) or not isinstance(claimed_hash, str):
        return False
    path = Path(raw_path).expanduser()
    return path.is_file() and sha256_file(path) == claimed_hash


def gate(gate_id: str, status: str, evidence: list[str], note: str) -> dict[str, Any]:
    return {"id": gate_id, "status": status, "evidence": evidence, "note": note}


def validate_run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    run_dir = Path(args.run_dir).expanduser()
    if not run_dir.is_absolute():
        raise ValueError("--run-dir must be absolute")
    run_dir = run_dir.resolve()
    run = load_json(run_dir / "run.json")
    scene = load_json(run_dir / "scene.json")
    asset = load_json(run_dir / "asset.json")
    blend = load_json(run_dir / "evidence" / "blend-inspection.json")
    renders = load_json(run_dir / "evidence" / "render-evidence.json")
    reproduction = load_json(run_dir / "evidence" / "reproduction.json")
    gltf = load_json(run_dir / "evidence" / "gltf-validation.json")
    browser = load_json(run_dir / "evidence" / "browser-runtime.json")
    host_smoke = load_json(run_dir / "evidence" / "host-smoke.json")
    gates: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []

    authority_ok = bool(run and scene and asset and asset.get("source", {}).get("sha256"))
    gates.append(gate("authority", "PASS" if authority_ok else "FAIL", ["run.json", "scene.json", "asset.json"] if authority_ok else [], "Declared run, scene, and asset authority are present." if authority_ok else "One or more authority contracts are missing or incomplete."))
    if not authority_ok:
        issues.append({"severity": "P0", "gate": "authority", "message": "Authority contracts are missing or incomplete."})

    reproduction_status = "PASS" if reproduction and reproduction.get("match") is True else ("FAIL" if reproduction else "UNVERIFIED")
    gates.append(gate("reproduction", reproduction_status, ["evidence/reproduction.json"] if reproduction else [], "Two normalized builds match." if reproduction_status == "PASS" else "Clean reproduction has not been proven."))

    scene_status = "PASS" if blend and blend.get("status") == "PASS" else ("FAIL" if blend else "UNVERIFIED")
    gates.append(gate("scene_integrity", scene_status, ["evidence/blend-inspection.json"] if blend else [], "Blender inspection passed." if scene_status == "PASS" else "Blender scene integrity is not proven."))
    required_views = {"front", "back", "left", "right", "top", "perspective"}
    rendered_views = {
        item.get("view")
        for item in (renders or {}).get("views", [])
        if verified_file_entry(item)
    }
    render_evidence_ok = bool(
        renders
        and renders.get("status") == "PASS"
        and required_views <= rendered_views
        and verified_file_entry(renders.get("contact_sheet"))
        and verified_file_entry(renders.get("lookdev"))
    )
    identity_ok = bool(
        blend
        and blend.get("coverage", {}).get("components_percent") == 100
        and blend.get("coverage", {}).get("materials_percent") == 100
        and render_evidence_ok
    )
    identity_status = "PASS" if identity_ok else ("FAIL" if blend else "UNVERIFIED")
    identity_evidence = []
    if blend:
        identity_evidence.append("evidence/blend-inspection.json")
    if renders:
        identity_evidence.append("evidence/render-evidence.json")
    gates.append(gate("identity", identity_status, identity_evidence, "Required component/material coverage and fixed-view render evidence are complete." if identity_ok else "Required identity coverage or fixed-view render evidence is incomplete or unverified."))

    gltf_errors = (gltf or {}).get("validator", {}).get("issues", {}).get("numErrors")
    summary = (gltf or {}).get("semantic", {})
    gltf_ok = bool(gltf and gltf_errors == 0 and summary.get("bytes", 10**18) <= 5 * 1024 * 1024 and summary.get("triangles", 10**18) <= 75000)
    gltf_status = "PASS" if gltf_ok else ("FAIL" if gltf else "UNVERIFIED")
    gates.append(gate("gltf", gltf_status, ["evidence/gltf-validation.json"] if gltf else [], "GLB validator and fixture budgets passed." if gltf_ok else "GLB validity or fixture budgets are not proven."))

    browser_screenshot = (browser or {}).get("desktop_screenshot")
    browser_screenshot_ok = verified_file_entry(browser_screenshot)
    cross_ok = bool(
        browser
        and browser.get("cross_runtime", {}).get("required_node_coverage_percent") == 100
        and browser.get("cross_runtime", {}).get("bbox_drift_percent", 100) <= 0.5
        and browser_screenshot_ok
    )
    cross_status = "PASS" if cross_ok else ("FAIL" if browser else "UNVERIFIED")
    gates.append(gate("cross_runtime", cross_status, ["evidence/browser-runtime.json"] if browser else [], "Browser and GLB semantic bounds agree." if cross_ok else "Cross-runtime parity is incomplete or unverified."))

    web_metrics = (browser or {}).get("metrics", {})
    candidate = run_dir / "assets" / "asset.glb"
    candidate_hash = sha256_file(candidate) if candidate.is_file() else "0" * 64
    web_ok = bool(
        browser
        and browser.get("status") == "ready"
        and browser.get("console_errors") == 0
        and browser.get("asset", {}).get("sha256") == candidate_hash
        and browser.get("network", {}).get("status") == "PASS"
        and browser.get("raf", {}).get("delta", 0) > 0
        and web_metrics.get("draw_calls", 10**9) <= 30
        and web_metrics.get("textures", 10**9) <= 8
        and web_metrics.get("frame_p95_ms", 10**9) <= 25
    )
    web_status = "PASS" if web_ok else ("FAIL" if browser else "UNVERIFIED")
    gates.append(gate("web_runtime", web_status, ["evidence/browser-runtime.json"] if browser else [], "Observed browser runtime and desktop fixture budget passed." if web_ok else "Browser runtime or desktop performance is incomplete or unverified."))

    delivery_files = [run_dir / "run.json", run_dir / "scene.json", run_dir / "asset.json", run_dir / "assets" / "asset.blend", run_dir / "assets" / "asset.glb"]
    required_evidence_files = [
        run_dir / "evidence" / "blend-inspection.json",
        run_dir / "evidence" / "render-evidence.json",
        run_dir / "evidence" / "reproduction.json",
        run_dir / "evidence" / "gltf-validation.json",
        run_dir / "evidence" / "browser-runtime.json",
    ]
    delivery_ok = (
        all(path.is_file() for path in [*delivery_files, *required_evidence_files])
        and all(item["status"] == "PASS" for item in gates)
    )
    gates.append(gate("delivery", "PASS" if delivery_ok else "FAIL", [str(path.relative_to(run_dir)) for path in [*delivery_files, *required_evidence_files] if path.is_file()], "Required delivery set and upstream gates passed." if delivery_ok else "Delivery set is incomplete or an upstream hard gate did not pass."))

    for item in gates:
        if item["status"] == "FAIL" and not any(issue.get("gate") == item["id"] for issue in issues):
            issues.append({"severity": "P1", "gate": item["id"], "message": item["note"]})
    optional_unverified = list(
        dict.fromkeys(
            [
                *(run or {}).get("unverified", []),
                *(browser or {}).get("unverified", []),
            ]
        )
    )
    for warning in (browser or {}).get("warnings", []):
        issues.append({"severity": "P2", "gate": "web_runtime", "message": str(warning)})
    overall = max((item["status"] for item in gates), key=lambda status: STATUS_RANK[status])
    skill_root = Path(__file__).resolve().parent.parent
    source_path = Path((asset or {}).get("source", {}).get("path", "<declared-source>"))
    commands = [
        " ".join(
            shlex.quote(part)
            for part in [
                "blender",
                "--background",
                "--factory-startup",
                "--python",
                str(source_path),
                "--",
                "--output-dir",
                str(run_dir / "assets"),
            ]
        ),
        " ".join(
            shlex.quote(part)
            for part in [
                "blender",
                "--background",
                str(run_dir / "assets" / "asset.blend"),
                "--python",
                str(skill_root / "scripts" / "blend_inspect.py"),
                "--",
                "--scene-contract",
                str(run_dir / "scene.json"),
                "--output",
                str(run_dir / "evidence" / "blend-inspection.json"),
            ]
        ),
        " ".join(
            shlex.quote(part)
            for part in [
                "blender",
                "--background",
                str(run_dir / "assets" / "asset.blend"),
                "--python",
                str(skill_root / "scripts" / "render_evidence.py"),
                "--",
                "--output-dir",
                str(run_dir / "evidence"),
            ]
        ),
        " ".join(
            shlex.quote(part)
            for part in [
                "node",
                str(skill_root / "scripts" / "gltf_validate.mjs"),
                str(run_dir / "assets" / "asset.glb"),
                "--output",
                str(run_dir / "evidence" / "gltf-validation.json"),
            ]
        ),
        " ".join(
            shlex.quote(part)
            for part in [
                "python3",
                str(skill_root / "scripts" / "3d_craft.py"),
                "validate",
                "--run-dir",
                str(run_dir),
                "--json",
            ]
        ),
    ]
    report = {
        "schema": "3d-craft.validation.v1",
        "command": "validate",
        "candidate_sha256": candidate_hash,
        "status": overall,
        "gates": gates,
        "evidence": sorted(
            {
                *{evidence for item in gates for evidence in item["evidence"]},
                *({"evidence/host-smoke.json"} if host_smoke else set()),
            }
        ),
        "issues": issues,
        "repairs": (run or {}).get("repairs", []),
        "delivery": {
            "files": [{"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in delivery_files if path.is_file()],
            "commands": commands,
            "unverified": [
                *[item["id"] for item in gates if item["status"] != "PASS"],
                *optional_unverified,
            ],
        },
    }
    report_path = run_dir / "reports" / "validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({k: v for k, v in report.items() if k != "command"}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
        else:
            payload, exit_code = validate_run(args)
        emit(payload, as_json=args.json, output=args.output)
        return exit_code
    except (OSError, ValueError) as error:
        print(f"3d-craft: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
