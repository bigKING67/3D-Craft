# 3D-Craft

3D-Craft is a portable, evidence-driven Agent Skill for building and validating
product/prop assets across Blender, GLB, and React Three Fiber.

Its core rule is simple: successful code execution is not finished 3D work.
Completion requires fixed-view visual evidence, scene inspection, GLB checks,
real browser runtime evidence, and a hash-bound delivery report.

## V0.1

The first candidate deliberately supports one narrow vertical slice:

```text
product or prop brief
→ Blender 5.2.1 LTS asset
→ six fixed views and scene inspection
→ Khronos-validated GLB
→ R3F viewer
→ browser67 runtime QA
→ evidence-bound validation
```

Reference reconstruction, characters, simulation, games, WebGPU, and MCP
bundling are deferred. See `docs/PRODUCT.md` and `docs/ROADMAP.md`.

## Source validation

```bash
npm install
npm run validate
npm test
npm run viewer:typecheck
npm run viewer:build
python3 skills/3d-craft/scripts/3d_craft.py doctor --json
```

## Local candidate install

The install is intentionally separate from source validation:

```bash
bash scripts/install_local.sh
```

It stages and validates a copy, backs up an existing installation, atomically
replaces `$HOME/.agents/skills/3d-craft`, verifies the installed copy, and emits
a provenance digest. Codex, Pi, and Agent Skills-compatible hosts can discover
the same canonical install. Root `package.json` also exposes the Skill through
`pi.skills` for project-scoped Pi use.

Host discovery and model invocation are separate acceptance boundaries. See
`docs/HOST_COMPATIBILITY.md` for scoped Codex, Pi, and Grok smoke commands,
host-runtime boundaries, and the evidence required before claiming support.

## Reproducible candidate package

Build a deterministic ZIP twice, compare SHA-256, validate an independently
extracted copy, and emit a local candidate attestation:

```bash
candidate_dir="$(mktemp -d /tmp/3d-craft-candidate.XXXXXX)"
python3 scripts/release_gate.py --output-dir "$candidate_dir/release" --json
```

The gate also runs source validation, unit/contract tests, viewer type checking,
and a viewer production build outside the installable Skill. A passing gate is
not release provenance when the source is dirty or has no immutable Git commit;
commit, push, tag, release, publish, and global installation remain separate
authorization and evidence boundaries.

## Canonical fixture

The original coffee grinder in `evals/coffee-grinder/` is generated without
third-party assets. Put run output outside the repository:

```bash
run_dir="$(mktemp -d /tmp/3d-craft-coffee-grinder.XXXXXX)"
python3 skills/3d-craft/scripts/3d_craft.py init-run \
  --project-key coffee-grinder --run-dir "$run_dir" --authoring-mode procedural --json
cp evals/coffee-grinder/scene.json "$run_dir/scene.json"
blender --background --factory-startup \
  --python evals/coffee-grinder/create_asset.py -- \
  --output-dir "$run_dir/assets"
```

Continue with the inspection, render, GLB, viewer, and browser commands in
`skills/3d-craft/SKILL.md`. Do not commit generated `.blend`, `.glb`, renders,
screenshots, or run state.

## Product boundary

Only `skills/3d-craft/` is installable. Root directories contain development,
evaluation, CI, packaging, and source-governance material. This repository is a
local candidate until commit, push, tag, release, and publish are each
authorized and independently verified.
