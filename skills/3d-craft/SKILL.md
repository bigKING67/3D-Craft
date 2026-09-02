---
name: 3d-craft
description: >
  Plan, create, inspect, refine, export, integrate, validate, and repair
  Blender, glTF/GLB, Three.js, WebGL, and React Three Fiber product or prop
  assets. Use for reproducible Blender production, Blender-to-web handoff,
  fixed-view render evidence, GLB validation, web 3D runtime QA, or a failing
  3D asset/viewer. V0.1 does not cover reference-image reconstruction,
  characters, simulation, games, or WebGPU.
license: MIT
metadata:
  author: bigKING67
  version: "0.1.0"
  compatibility: "Portable across Agent Skills hosts; deterministic automation requires Python 3, Node.js 22.12+, Blender 5.2.1 LTS, and Chromium; browser runtime evidence uses browser67; MCP integrations are optional and not bundled."
---

# 3D Craft

Create and deliver 3D work through a visible, reproducible, evidence-bound
production loop. Do not use successful code execution as the completion
criterion. Completion requires the applicable asset, visual, structural,
handoff, runtime, and delivery gates.

## V0.1 product boundary

Support these workflows:

- create a product or prop in Blender from a text brief;
- inspect or repair an existing product/prop `.blend` or `.glb`;
- export Blender work to a validated GLB;
- integrate a GLB into Three.js or React Three Fiber;
- validate a web 3D viewer in a real browser;
- produce a hash-bound evidence and validation report.

Return `unsupported_in_v0_1` for reference-image reconstruction, characters,
sculpting, rigging, complex animation, simulation, games, WebGPU, NeRF,
Gaussian splats, photogrammetry, or external AI 3D generation. Explain the
nearest supported slice without pretending the full request was completed.

## Start here

1. Establish the target, intent, profile, quality tier, authoring mode, and
   evidence level.
2. Run `scripts/3d_craft.py route` with fixed enum values.
3. Read only the references named by the route result.
4. Run `scripts/3d_craft.py doctor --json` before tool-backed work.
5. Declare the durable authoring authority and output boundary.
6. Create or load the scene contract before building.
7. Work in causal stages and stop at the first failed hard gate.
8. Bind every delivered claim to observed evidence, hashes, and versions.

For an end-to-end product asset, the default route is:

```bash
python3 scripts/3d_craft.py route \
  --target bridge \
  --intent build \
  --profile product-asset \
  --quality-tier production \
  --authoring-mode hybrid \
  --evidence-level assured \
  --json
```

Use `procedural` when a Blender Python script is the source of truth. Use
`native` when a `.blend` file is the source of truth. Use `hybrid` for normal
production: the `.blend` owns artistic geometry and deterministic scripts own
normalization, inspection, and export.

## Routing contract

Use only these V0.1 values:

- `target`: `blender`, `bridge`, `web3d`
- `intent`: `build`, `validate`, `repair`
- `profile`: `product-asset`, `prop`
- `quality_tier`: `draft`, `production`
- `authoring_mode`: `procedural`, `native`, `hybrid`
- `evidence_level`: `static`, `rendered`, `runtime`, `assured`

Do not invent a route as free text. A valid route returns selected references,
required capabilities, hard gates, and explicit unsupported features.

## Authority and evidence

Read `references/authority-and-evidence.md` for every task. Keep these states
distinct:

- `SPECIFIED`: required by a brief, contract, or user instruction;
- `OBSERVED`: directly read from a file, command, renderer, or runtime;
- `INFERRED`: derived from observed evidence with a stated chain;
- `HYPOTHESIZED`: a testable explanation not yet confirmed;
- `UNVERIFIED`: required evidence was unavailable or not run.

Never promote source presence to render proof, a screenshot to interaction
proof, desktop evidence to mobile GPU proof, or a tool plan to a run receipt.
Every visual, performance, and runtime conclusion names its evidence artifact.

Keep run state outside the source repository by default:

```text
$THREE_D_CRAFT_RUN_ROOT/<project-key>/<run-id>/
```

When the environment variable is unset, use the operating system state-data
directory. An explicit absolute `--run-dir` always wins. User-selected final
assets may be copied to their delivery location only after validation.

## Capability discovery

Ask for capabilities rather than one product-specific MCP:

```text
blender.version
blender.inspect
blender.execute
blender.render
blender.export
asset.gltf.validate
asset.gltf.inspect
web.scene.inspect
browser.navigate
browser.capture
browser.console.read
browser.network.read
browser.performance.profile
```

V0.1 prefers Blender headless CLI for Blender work and browser67 for browser
work. Do not fall back from browser67 to an in-app browser. A missing optional
capability makes its gate `UNVERIFIED`; it does not authorize fabricated
evidence.

## Production workflow

### 0. Preflight

Confirm the authority file, write boundary, Blender version, target runtime,
asset licenses, allowed execution, delivery format, and available tools.
Record them in `run.json`. Do not execute unknown Blender add-ons or scripts,
download unlicensed assets, upload private models, or connect to a personal
browser profile.

### 1. Scene contract

Define units, Z-up authoring coordinates, dimensions, origin policy,
components, materials, identity features, cameras, web runtime, budgets, and
required evidence. Unknown budgets are `provisional`, never measured facts.

### 2. Blockout

Resolve primary scale, silhouette, part count, relative placement, and camera
framing. Do not spend time on micro-bevels, complex shaders, or decorative
lighting while the shape contract still fails.

### 3. Structural gate

Inspect dimensions, transforms, hierarchy, naming, topology, normals, UVs,
materials, missing textures, cameras, and lights. Render fixed front, back,
left, right, top, and perspective views. Failed proportions return to
blockout; materials do not conceal a shape failure.

### 4. Production modeling and look development

Create deliberate topology, bevels, smoothing, pivots, material regions, PBR
values, UVs, light shape, and camera composition. Read
`references/blender-production.md` for the deterministic Blender boundary.

### 5. GLB handoff

Export with fixed settings, run Khronos validation, then inspect semantic node,
material, primitive, texture, animation, extension, bounding-box, and file-size
facts. Read `references/gltf-web-handoff.md`. Compression is valid only when the
viewer has the corresponding decoder and the optimized asset is revalidated.

### 6. Web integration

Own Loading, Ready, Error, resize, camera framing, color management, tone
mapping, shadows, interaction, cleanup, and reduced motion. In development and
tests, expose the read-only `window.__THREE_D_CRAFT__` observability snapshot.

### 7. Browser runtime QA

Read `references/web3d-runtime-qa.md`. Use a browser67-managed dedicated tab,
background-preferred. Wait for semantic readiness, inspect console and network,
verify RAF progress and renderer statistics, test remount/dispose behavior, and
check desktop plus mobile layout. A final screenshot may use one bounded
foreground interval; restore or finalize the exact managed task afterward.

### 8. Validation and repair

Aggregate the applicable gates as `PASS`, `FAIL`, `UNVERIFIED`, or `BLOCKED`.
If a gate fails, read `references/repair-and-security.md` and make the smallest
causal repair. Re-run the same evidence. Stop after three repair attempts and
report the remaining blocker.

## Hard gates

Apply only relevant gates, but never waive one silently:

- `authority`: durable source, version, inputs, hashes, and authorization;
- `reproduction`: clean rebuild or deterministic re-export;
- `scene_integrity`: dimensions, transforms, hierarchy, topology, materials;
- `identity`: required components, proportions, silhouette, key features;
- `gltf`: valid GLB and complete semantic contract;
- `cross_runtime`: asset bounds, pose, materials, and key components survive;
- `web_runtime`: visible model, no blocking error, functioning interaction and
  lifecycle cleanup;
- `delivery`: declared files, evidence, hashes, versions, and limitations.

A hard-gate failure produces `FAIL` without a compensating total score. V0.1
does not issue a numeric quality score.

## Default V0.1 fixture budgets

These values are approved only for the bundled coffee-grinder evaluation:

- GLB size at most 5 MiB;
- triangles at most 75,000;
- draw calls at most 30;
- textures at most 8;
- frame p95 at most 25ms at 1440x900 in current Mac Chrome, after a three-
  second warmup and over a ten-second sample;
- cross-runtime bounding-box drift at most 0.5 percent;
- required node and material coverage exactly 100 percent;
- front and perspective flat-mask IoU at least 0.92 when comparable captures
  are actually available.

Mobile layout is required. Mobile GPU performance remains `UNVERIFIED` unless
measured on an approved target device.

## Deterministic tools

Run tools from the Skill directory or use absolute paths:

```bash
python3 scripts/3d_craft.py doctor --json
python3 scripts/3d_craft.py init-run --project-key demo --json
blender --background asset.blend --python scripts/blend_inspect.py -- \
  --output /absolute/run/evidence/blend-inspection.json
blender --background asset.blend --python scripts/render_evidence.py -- \
  --output-dir /absolute/run/evidence
node scripts/gltf_validate.mjs asset.glb \
  --output /absolute/run/evidence/gltf-validation.json
python3 scripts/3d_craft.py validate \
  --run-dir /absolute/run --json
```

JSON modes write machine output to stdout and diagnostics to stderr. A real
failure exits nonzero. Do not parse human prose as a machine contract.

## Delivery

Deliver only what was produced and checked:

- route and authoring authority;
- source and derived asset paths with SHA-256;
- Blender and runtime versions;
- inspection, fixed-view render, GLB, browser, and performance evidence;
- gate status and issue list;
- exact reproducibility commands;
- repairs attempted and same-evidence verdicts;
- unsupported, skipped, and unverified scope.

For visible web work, distinguish build success, managed browser behavior,
screenshot artifact, and final visual review. A screenshot existing is not a
visual-review pass by itself.
