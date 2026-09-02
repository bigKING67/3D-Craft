# Authority and evidence

Read this for every routed task.

## Durable authority

Choose one and record it before mutation:

- `procedural`: the creation script is primary; `.blend` and `.glb` are derived.
- `native`: the `.blend` file is primary; export settings and manifest make the
  handoff reproducible.
- `hybrid`: `.blend` owns artistic source while scripts own normalization,
  inspection, and export.

Record source hashes, input hashes, tool versions, output paths, licenses, and
manual steps. Reproduction compares normalized scene and GLB semantic facts,
not volatile `.blend` bytes.

## Evidence language

Use `SPECIFIED`, `OBSERVED`, `INFERRED`, `HYPOTHESIZED`, and `UNVERIFIED`.
Every `OBSERVED` claim names the file, command, screenshot, or runtime receipt.
Every inference states the evidence it derives from. Never describe an unseen
back side, unmeasured FPS, unopened browser, or unrun host as observed.

## State and files

Store the active state in `run.json`; use `scene.json`, `asset.json`, and
`validation.json` for stable contracts. Evidence files are immutable per
candidate hash. If a repair changes the candidate, generate new evidence rather
than overwriting the prior receipt.

Run data defaults outside the repository. Generated assets may enter a delivery
directory only when the user chose it. Do not place screenshots, render frames,
or Blender backup files beside source code.

## Status semantics

- `PASS`: decisive evidence satisfies the gate.
- `FAIL`: decisive evidence contradicts the gate.
- `UNVERIFIED`: evidence was not available or not run.
- `BLOCKED`: a prerequisite prevents evaluation.

Never average a hard failure into a passing score. V0.1 reports gate status,
not a numeric score.
