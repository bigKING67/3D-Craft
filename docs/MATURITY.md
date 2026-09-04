# Maturity

## V0.1 status: local candidate

The current source implements the narrow product/prop vertical slice across
Blender, GLB, an R3F viewer, browser runtime evidence, and evidence-bound
validation. Local acceptance has exercised:

- current Codex Skill frontmatter validation;
- source, unit, schema-contract, and viewer type/build checks;
- deterministic package construction with two-build SHA-256 parity;
- validation of an independently extracted package, including execution of its
  bundled Khronos validator against a minimal GLB and an isolated doctor
  capability probe;
- isolated, non-global local installation;
- two clean coffee-grinder Blender builds with matching normalized scene and
  GLB semantic digests;
- live Blender failure propagation: an uncaught automation error returned `0`
  without a policy flag and returned `2` with the now-required
  `--python-exit-code 2`;
- contract-framed six-view rendering for both the 32 cm fixture and an
  independent 2 m generic product root without fixture-name assumptions;
- the coffee-grinder browser runtime through GLB byte/hash verification, 100%
  node-name coverage, visible RAF progression, remount/dispose, and desktop
  performance evidence;
- the production Viewer dependency boundary: a 5.98 KB application entry and
  196.26 KB initial JavaScript path before the async AssetScene/R3F/Three
  runtime, with the pinned Three r185 chunk held under an explicit 800 KB
  regression ceiling;
- production browser readiness after a verified 1280x720 viewport transaction,
  including GLB HTTP success, populated 15-object/13-mesh/5-material metrics,
  expected 188x224x320 mm dimensions, and a live WebGL context;
- visible browser67 visual evidence from the current Viewer tree: the final
  1280x720 desktop sample has no page overflow and keeps the complete evidence
  rail and asset in frame, while the final 390px-wide full-page sample keeps
  the complete asset in the responsive Canvas. Both captures verified
  `visibilityState=visible`, exact requested viewport metrics, PNG dimensions,
  and automatic viewport-override cleanup;
- separate Skill discovery and invocation smokes for Codex, Pi, and Grok.

These checks establish a local candidate, not a published release. Evidence is
valid only for the exact source tree, host versions, providers, Blender build,
browser runtime, and artifacts recorded by the corresponding receipt.

## Not yet established

- immutable Git commit provenance;
- remote CI results for the candidate commit;
- tag, GitHub Release, registry publication, or public package parity;
- global user installation parity;
- Windows or Linux host acceptance;
- physical mobile-device GPU frame timing;
- physical target-device evidence for the new Viewer split, including cold-load
  paint timing, cache reuse, and mobile GPU frame timing. Current bundle and
  browser observations prove the dependency boundary and semantic readiness,
  not an end-user performance improvement;
- the deferred V0.2+ profiles listed in `ROADMAP.md`.

Commit, push, tag, release, publish, and global installation remain separate
authorization boundaries. A local candidate gate must report
`release_eligible=false` whenever the source has no commit or the worktree is
dirty.
