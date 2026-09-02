# glTF and web handoff

## Export

Use a fixed Blender export configuration: GLB container, selected coordinate
conversion, applied modifiers, materials, cameras only when required, animation
only when required, extras when they carry declared semantic metadata, and no
unlicensed embedded resources.

## Validation

Khronos validation is necessary but not sufficient. Also inspect:

- node names and hierarchy;
- required material names and assignments;
- mesh and primitive counts;
- triangle count and bounding box;
- texture count, dimensions, MIME types, and color-space intent;
- animation names and duration when applicable;
- used and required extensions;
- unused resources and GLB byte size.

The V0.1 validator parses the GLB JSON chunk and reports a semantic digest.
Bind the report to the GLB SHA-256.

## Web integration

Configure Draco, KTX2, or Meshopt decoders only when the asset actually uses
them. Treat exporter compression and loader support as one contract. Own
loading, error, camera framing, resize, tone mapping, color space, shadows,
interaction, resource disposal, and context-loss behavior. Revalidate after
every optimization and compare visual evidence before accepting size gains.

Keep runtime dependencies and generated assets out of the installed Skill.
Copy the viewer template into a run-owned directory, then use its nested lock:

```bash
viewer_run_dir="$(mktemp -d /tmp/3d-craft-viewer.XXXXXX)"
cp -R assets/r3f-viewer/. "$viewer_run_dir/"
cp /absolute/run/assets/asset.glb "$viewer_run_dir/public/asset.glb"
cd "$viewer_run_dir"
npm ci
VITE_ASSET_SHA256=<asset-sha256> npm run dev
```

`node_modules`, Vite cache, build output, TypeScript build info, and candidate
GLBs are runtime state. They must not be packaged into `skills/3d-craft/`.
