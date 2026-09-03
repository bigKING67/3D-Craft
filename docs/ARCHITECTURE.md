# Architecture

## Product boundary

`skills/3d-craft/` is the only installable product. It contains portable Agent
instructions, references, schemas, deterministic scripts, and a small R3F
viewer template. Root-level docs, tests, evaluations, CI, and governance files
support development and do not become Skill runtime dependencies.

## Layers

1. **Skill router** — resolves target, intent, profile, quality tier, authoring
   mode, and evidence level to a small reference set and capability list.
2. **Contracts** — capture run state, scene requirements, asset provenance, and
   validation gates as versioned JSON.
3. **Deterministic tools** — inspect Blender files, render fixed views, and
   validate GLB without requiring an MCP or repository-level npm install. The
   minimal audited Khronos validator runtime is bundled with its license and
   notices.
4. **Viewer fixture** — renders a GLB and exposes a read-only development
   observability contract for browser QA.
5. **Evidence closeout** — binds claims to files, SHA-256 digests, commands,
   versions, and observed results. Render scripts prove image production;
   feature-level visual assessment remains an explicit, separately bound
   reviewer action.
6. **Upstream governance** — keeps researched sources, relevant-path freshness,
   license decisions, local destinations, and validation cases outside the
   installed product. See `../UPSTREAM.md` and `../upstreams.lock.json`.

## Authoring authority

- `procedural`: a Blender Python script is the durable source.
- `native`: a `.blend` file is the durable source, with pinned export settings.
- `hybrid`: the `.blend` file owns artistic geometry and a deterministic script
  owns normalization, inspection, and export. This is the production default.

Reproducibility means the declared authority can regenerate or re-export the
deliverable and its semantic manifest. It does not require `.blend` byte-for-
byte equality.

Commands stored in a validation report are candidate-scoped invocation
receipts. Replaying them requires substituting a new empty run directory;
evidence producers deliberately refuse to overwrite the recorded run.

## Tool boundary

Core instructions request capabilities such as `blender.inspect`,
`asset.gltf.validate`, or `browser.capture`; they do not hard-code one MCP.
V0.1 implements Blender through its headless CLI and browser evidence through
browser67. Blender MCP, Three.js DevTools MCP, and Chrome DevTools MCP are
deferred adapters.

## Runtime observability

The development viewer exposes `window.__THREE_D_CRAFT__`. It is a read-only
snapshot with schema version, lifecycle state, asset identity, object counts,
renderer statistics, RAF progress, mount/dispose counters, and an error
summary. It exists only in development/test builds and is not a production API.
