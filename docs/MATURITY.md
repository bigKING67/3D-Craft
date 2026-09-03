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
- current-tree assured browser screenshots: the latest browser67 capture calls
  timed out repeatedly, including on a fresh managed tab, so desktop/mobile
  screenshot and responsive-layout gates remain `BLOCKED` rather than being
  credited from a stale sample;
- fixture Viewer JavaScript chunk optimization: the current production build
  succeeds but Vite reports a roughly 1.14 MB minified / 314 KB gzip main
  chunk, which remains visible as a non-blocking V0.1 performance warning;
- the deferred V0.2+ profiles listed in `ROADMAP.md`.

Commit, push, tag, release, publish, and global installation remain separate
authorization boundaries. A local candidate gate must report
`release_eligible=false` whenever the source has no commit or the worktree is
dirty.
