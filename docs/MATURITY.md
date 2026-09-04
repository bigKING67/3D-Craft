# Maturity

## V0.1 status: locally sealed candidate

The product code at commit
`fe5b05c6ec6a8cea781ef72aeeb22938a30beec2` implements the narrow
product/prop vertical slice across Blender, GLB, an R3F viewer, browser runtime
evidence, and evidence-bound validation. Local acceptance has exercised:

- current Codex Skill frontmatter validation;
- source, unit, schema-contract, and viewer type/build checks;
- deterministic package construction with two-build SHA-256 parity;
- the complete release gate from a clean detached worktree at that exact
  commit, with `release_eligible=true` and local package SHA-256
  `52e88bba6c84c50867c165c2e4a3a04a78c77aa82c694d2aba8bf8d0a206d3e7`;
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
- production browser readiness after a verified 1440x900 viewport transaction,
  including GLB HTTP success, populated 15-object/13-mesh/5-material metrics,
  expected 188x224x320 mm dimensions, and a live WebGL context;
- visible browser67 visual evidence bound to candidate GLB SHA-256
  `1c2fbd8291ac9b5285fa1a15a95327ecf791af741f7c8408211e5ead3093396c`:
  the final 1440x900 desktop sample has no page overflow and keeps the complete
  evidence rail and asset in frame, while the final 390px-wide full-page sample
  keeps the complete asset in the responsive Canvas. Both captures verified
  `visibilityState=visible`, exact requested viewport metrics, PNG dimensions,
  and automatic viewport-override cleanup;
- causal browser interaction evidence: a pointer orbit moved the camera,
  reset-camera restored it with zero measured position error, remount/dispose
  counters advanced, a clean reload returned to `ready`, and the served GLB
  bytes matched the candidate hash;
- copied, run-owned desktop and mobile screenshots under the external assured
  run at `~/Library/Application Support/3d-craft/runs/coffee-grinder/v01-seal-20260904`,
  with all eight routed gates and 21 delivery files passing validation;
- separate Skill discovery and invocation smokes for Codex, Pi, and Grok.

On 2026-09-04, the exact installable Skill tree from commit
`346fba0616ea574c3f7080511dd7d46f2e8f6159` was also installed to the canonical
user-global path `~/.agents/skills/3d-craft`. The 36 source and installed files
matched byte-for-byte, source and Codex Skill validation passed, and discovery
from the independent `resume` workspace passed on Codex 0.153.2, Pi 0.80.6, and
Grok 1.0.5. The installation provenance tree digest was
`211ea7211e56153ee3ce5acfd51b5ec02f5a223455d75202408de27f0fe50dcd`.
This establishes local macOS global-install and discovery parity only; no model
invocation, credential access, or provider configuration was part of that
acceptance.

These checks establish a locally sealed candidate, not a published release.
Evidence is valid only for the exact commit, host versions, providers, Blender
build, browser runtime, and artifacts recorded by the corresponding receipt.
The browser report retains one non-blocking Three.js deprecation warning, and
mobile capture remains layout evidence rather than physical-device GPU proof.

## Post-seal working-tree verification

The uncommitted browser-evidence binder refinement was exercised separately in
`~/Library/Application Support/3d-craft/runs/coffee-grinder/v01-binder-20260904`.
That fresh run bound a cache-bypassed browser fetch to candidate GLB SHA-256
`120e6ab9e2ef56a06cb9d01a92a2b77c179c2513f0db03a6d6e976660225bf8d`,
copied visually reviewed 1440x900 desktop and 390px mobile screenshots into the
run, rejected a hidden readiness screenshot as `INVALID SAMPLE`, and passed all
eight routed gates. Native orbit input changed the camera, reset restored it,
remount/dispose advanced, a clean reload returned to `ready`, and a clean
three-second console observation contained no errors and one non-blocking
Three.js `Clock` deprecation warning.

That warning was traced to `@react-three/fiber` 9.7.0 constructing
`THREE.Clock`; Three.js deprecated that class in r183. On 2026-09-04 the npm
stable tags still resolved to R3F 9.7.0, Drei 10.7.8, and Three.js 0.185.1, so
there was no newer stable R3F line to adopt. The viewer does not suppress the
warning, patch `node_modules`, downgrade Three.js, or move to the R3F 10 alpha
line merely to produce a clean report. It remains an explicit P2 compatibility
issue until a stable upstream migration is available and revalidated.

This verification was initially produced from a dirty working tree, so it does
not by itself extend the immutable release provenance of commit
`fe5b05c6ec6a8cea781ef72aeeb22938a30beec2`. Binder release provenance exists
only when a later external release attestation names an exact clean commit;
this narrative does not self-certify that transition.

## Not yet established

- remote CI results for the candidate commit;
- tag, GitHub Release, registry publication, or public package parity;
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
dirty. The referenced detached proof reports `true` only for
`fe5b05c6ec6a8cea781ef72aeeb22938a30beec2`; later source or documentation
changes require a new clean gate before inheriting that provenance claim.
