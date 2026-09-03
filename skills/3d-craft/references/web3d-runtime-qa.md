# Web 3D runtime QA

## Browser authority

Use browser67 for real-browser work. Select or create a managed dedicated tab
with `active:false`; preserve user tabs and profiles. Do not fall back to the
in-app browser. A bounded foreground interval is allowed only for final visual
acceptance when the user has authorized it.

## Readiness

Wait for the viewer observability snapshot to report `status: ready`. Verify
that `document.visibilityState` is appropriate for the claim, RAF counters
advance, the canvas has nonzero dimensions, the camera and renderer exist, and
object/mesh/triangle counts agree with the loaded asset. Compare the frozen
`scene.nodeNames` and `scene.materialNames` lists with the GLB semantic report;
do not infer node coverage from counts alone. A stale screenshot or DOM/3D
disagreement is `INVALID SAMPLE`.

## Checks

- console has no blocking errors;
- GLB request succeeds without unexpected redirects or decoder errors;
- model is visible and framed;
- orbit, zoom, and reset-camera work;
- resize does not create a canvas loop or overflow;
- remount/unmount increments lifecycle counters and disposes owned resources;
- reduced motion removes nonessential automatic drift;
- desktop 1440x900 and mobile 390x844 layout are usable;
- desktop warmup/sample performance meets the approved fixture budget.

Mobile viewport testing proves layout only. It is not mobile GPU evidence.

If a required browser67 prerequisite repeatedly fails while the page itself is
still healthy, write `status: BLOCKED`, `page_status: ready`, name the failed
capability in `blocker`, and preserve the successful partial observations. Do
not substitute a stale or unreviewed screenshot; validation propagates the
blocked state to browser gates while retaining evidence-backed capabilities.

The bundled development viewer accepts a `3d-craft:test-remount` DOM event for
test orchestration. This event is registered only in Vite development mode;
the public observability snapshot remains frozen and read-only.
Use the viewer's `?motion=reduce` query for deterministic screenshots and
verify the visible `Reduced motion` label before accepting the sample.

## Closeout

Capture artifact path, SHA-256, dimensions, target, browser identity, and task
scope. Perform a visual consistency review after capture. Copy accepted desktop
and required mobile screenshots into the run-owned `evidence/` directory and
bind those copied bytes in `browser-runtime.json`; browser67 cache paths may be
retained as provenance but do not satisfy portable delivery. Finalize the exact
managed browser task; do not close or clean unrelated tabs or instances.
