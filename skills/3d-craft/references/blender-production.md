# Blender production

## Supported baseline

V0.1 targets Blender 5.2.1 LTS and uses `blender --background
--factory-startup` for deterministic automation. Reject a major/minor mismatch
unless the task explicitly accepts compatibility risk.

## Build order

1. clear the factory scene;
2. establish meters, Z-up source coordinates, frame rate, and color management;
3. create named root, component, camera, and light objects;
4. apply transforms intentionally and place the required origin/pivots;
5. build primary volumes before bevels and small details;
6. create named materials with Web-compatible Principled BSDF inputs;
7. save the authoritative `.blend`;
8. inspect, render, export, and validate without manual hidden steps.

## Inspection floor

Record Blender version, scene units, object hierarchy, dimensions, object and
mesh counts, triangle count, unapplied transforms, material assignments,
missing external files, non-manifold edges, custom normals, UV layers,
modifiers, cameras, lights, armatures, and animation clips.

Unapplied transforms are not automatically wrong, but they must be intentional
and compatible with export. Non-manifold geometry is a hard failure for closed
product surfaces unless the contract explicitly permits an open sheet.

## Render evidence

Use fixed front, back, left, right, top, and perspective cameras. Store camera
transforms, lens or orthographic scale, resolution, renderer, color transform,
file hash, and candidate asset hash. Structural evidence favors flat, readable
materials. Look-development evidence uses EEVEE with fixed lights. Do not move
the camera between candidates when comparing a repair.

## Reproduction

Run the canonical procedural fixture twice from `--factory-startup`. Compare a
normalized manifest of names, types, hierarchy, transforms, dimensions,
materials, triangle counts, and GLB semantic digest. `.blend` byte equality is
not required because Blender files may contain volatile metadata.
