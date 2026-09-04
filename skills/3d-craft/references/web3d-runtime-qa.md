# Web 3D runtime QA

## Browser authority

Use browser67 for real-browser work. Select or create a managed dedicated tab
with `active:false`; preserve user tabs and profiles. Do not fall back to the
in-app browser. A bounded foreground interval is allowed only for final visual
acceptance when the user has authorized it.

## Readiness

For a production build in a background-managed tab, establish the target
viewport before waiting for 3D readiness and verify the actual page metrics.
If the runtime chunks have loaded, Console has no blocking error, and the page
still remains at `loading`, run one bounded browser67 viewport capture
transaction, verify the requested inner dimensions and PNG dimensions, then
recheck semantic readiness. This transaction may wake a deferred R3F canvas
measurement; it is a readiness stimulus, not visual acceptance. If
`document.visibilityState` remains `hidden`, label the screenshot
`INVALID SAMPLE` even when the DOM, GLB request, and WebGL context become ready.

In development or test mode, wait for the viewer observability snapshot to
report `status: ready`. In a production build, the browser-exposed snapshot is
intentionally absent; wait for the semantic status UI to report `ready`, then
verify the GLB request, populated asset metrics, and a live WebGL context. Do
not weaken production privacy by exposing the development snapshot.

When the snapshot is available, verify that `document.visibilityState` is
appropriate for the claim, RAF counters advance, the canvas has nonzero
dimensions, the camera and renderer exist, and object/mesh/triangle counts
agree with the loaded asset. Compare the frozen `scene.nodeNames` and
`scene.materialNames` lists with the GLB semantic report; do not infer node
coverage from counts alone. A stale screenshot or DOM/3D disagreement is
`INVALID SAMPLE`.

## Checks

- console has no blocking errors;
- GLB request succeeds without unexpected redirects or decoder errors;
- model is visible and framed;
- orbit, zoom, and reset-camera work;
- resize does not create a canvas loop or overflow;
- remount/unmount increments lifecycle counters and disposes owned resources;
- context loss changes the visible state away from `ready`, pauses camera
  controls, restores the renderer, shows fresh RAF progress afterward, and
  preserves scene identity;
- reduced motion removes nonessential automatic drift;
- desktop 1440x900 and mobile 390x844 layout are usable;
- desktop warmup/sample performance meets the approved fixture budget.

Mobile viewport testing proves layout only. It is not mobile GPU evidence.

### Pinned V0.1 timing warning

The pinned stable viewer stack (`@react-three/fiber` 9.7.0,
`@react-three/drei` 10.7.8, and Three.js r185) emits one warning because the
R3F root store still constructs `THREE.Clock`, which Three.js deprecated in
r183 in favor of `THREE.Timer`. Preserve the exact warning as a P2 issue when
the clean observation has zero errors and the runtime otherwise passes. Do not
silence `console.warn`, edit installed dependencies, downgrade Three.js, or
adopt an alpha R3F release merely to make the evidence appear clean. Recheck
the stable dependency line during the next planned viewer-stack update and
remove this exception when R3F migrates its clock implementation. This is not
a blanket warning allowlist: diagnose and record every other warning normally.

If a required browser67 prerequisite repeatedly fails while the page itself is
still healthy, write `status: BLOCKED`, `page_status: ready`, name the failed
capability in `blocker`, and preserve the successful partial observations. Do
not substitute a stale or unreviewed screenshot; validation propagates the
blocked state to browser gates while retaining evidence-backed capabilities.

The bundled development viewer accepts a `3d-craft:test-remount` DOM event for
test orchestration. It also accepts `3d-craft:test-context-loss` and
`3d-craft:test-context-restore`; these call Three.js's real
`WEBGL_lose_context` path rather than simulating a CSS-only state. These events
and the browser-exposed observability snapshot are registered only in Vite
development or test mode; the snapshot remains frozen and read-only when
present. Its absence in production is expected.

Context-loss evidence is a forward-compatible V0.2 extension of the v1 browser
receipt. It remains optional for V0.1 receipts. When present, a `PASS` requires
extension support, at least one observed loss and restore, a return to visible
`ready`, and new RAF progress after restoration. A reported `FAIL` blocks the
`web_runtime` gate; do not omit a failed observation to manufacture a pass.
R3F may continue scheduling JavaScript RAF callbacks while the WebGL context is
lost, so `lifecycle.context.status` is the interruption authority; do not claim
the browser RAF itself stopped unless a separate observation proves it.
Use the viewer's `?motion=reduce` query for deterministic screenshots and
verify the visible `Reduced motion` label before accepting the sample.

## Closeout

Capture artifact path, SHA-256, dimensions, target, browser identity, and task
scope. Perform a visual consistency review after capture. Put the observations
and browser67 cache paths in an external draft, then seal them with:

```bash
python3 scripts/3d_craft.py bind-browser-evidence \
  --run-dir /absolute/run \
  --observation /absolute/browser-runtime-draft.json \
  --json
```

The draft uses schema name `3d-craft.browser-runtime-draft.v1`. It contains
observed runtime facts, not a second candidate manifest. Do not include
`runtime`, `asset`, destination paths, screenshot hashes, byte counts, or PNG
dimensions: the command derives those facts. A minimal ready draft is:

```json
{
  "schema": "3d-craft.browser-runtime-draft.v1",
  "status": "ready",
  "asset_url": "/asset.glb",
  "console_errors": 0,
  "network": {
    "status": "PASS",
    "bytes": 123456,
    "sha256": "replace-with-the-observed-served-glb-sha256"
  },
  "raf": {"delta": 60},
  "metrics": {"draw_calls": 12, "textures": 2, "frame_p95_ms": 14.5},
  "lifecycle": {
    "remount_test_status": "PASS",
    "ready_after_clean_reload": true,
    "context_loss": {
      "test_status": "PASS",
      "supported": true,
      "losses": 1,
      "restores": 1,
      "ready_after_restore": true,
      "raf_resumed_after_restore": true
    }
  },
  "cross_runtime": {
    "required_node_coverage_percent": 100,
    "bbox_drift_percent": 0.1
  },
  "desktop_screenshot": {
    "source_path": "/absolute/browser67-desktop.png",
    "css_viewport": [1440, 900],
    "device_pixel_ratio": 1,
    "capture_target": "viewport",
    "visibility_state": "visible",
    "horizontal_overflow": false,
    "visual_review": "PASS"
  },
  "responsive_layout": {
    "status": "PASS",
    "horizontal_overflow": false,
    "viewport": [390, 844],
    "scroll_extent": [390, 1269]
  },
  "mobile_screenshot": {
    "source_path": "/absolute/browser67-mobile.png",
    "css_viewport": [390, 844],
    "device_pixel_ratio": 1,
    "capture_target": "full_page",
    "visibility_state": "visible",
    "horizontal_overflow": false,
    "visual_review": "PASS",
    "note": "Responsive layout evidence only; physical mobile GPU is unverified."
  },
  "warnings": [],
  "unverified": ["Physical-mobile GPU frame timing was not measured."]
}
```

Replace the example bytes and SHA-256 with the values observed from the actual
network response. The command fails closed if those values differ from the
current run's `asset.glb`, if visibility is not `visible`, or if PNG dimensions
contradict the stated CSS viewport and DPR. It refuses to overwrite any sealed
report or screenshot. On success, accepted screenshots live in run-owned
`evidence/`; browser67 cache paths remain provenance only.

For `status: BLOCKED`, set `page_status: ready` and a nonempty `blocker`.
Screenshots may be omitted when capture itself is the blocker; do not invent a
file to satisfy the contract. For `network.status: FAIL`, response bytes and
SHA-256 may likewise be omitted because no successful asset response exists.

Finalize the exact managed browser task after capture. Do not close or clean
unrelated tabs or instances.
