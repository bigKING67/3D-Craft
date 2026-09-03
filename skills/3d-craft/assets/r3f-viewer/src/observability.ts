export type ViewerStatus = 'loading' | 'ready' | 'error'

export interface ThreeDCraftSnapshot {
  readonly schema: '3d-craft.web-observability.v1'
  readonly version: '0.1.0'
  readonly status: ViewerStatus
  readonly asset: Readonly<{ url: string; sha256: string }>
  readonly viewport: Readonly<{ width: number; height: number; dpr: number }>
  readonly scene: Readonly<{
    objects: number
    meshes: number
    materials: number
    dimensions: readonly [number, number, number]
    nodeNames: readonly string[]
    materialNames: readonly string[]
    camera_position: readonly [number, number, number]
  }>
  readonly renderer: Readonly<{
    calls: number
    triangles: number
    geometries: number
    textures: number
  }>
  readonly raf: Readonly<{
    status: 'idle' | 'running'
    frame_count: number
    last_frame_at_ms: number | null
    frame_p50_ms: number | null
    frame_p95_ms: number | null
  }>
  readonly lifecycle: Readonly<{ mounts: number; remounts: number; disposes: number }>
  readonly error: Readonly<{ message: string }> | null
}

declare global {
  interface Window {
    __THREE_D_CRAFT__?: ThreeDCraftSnapshot
  }
}

const lifecycle = { mounts: 0, remounts: 0, disposes: 0 }
let current: ThreeDCraftSnapshot | undefined

export function noteMount(): void {
  lifecycle.mounts += 1
  if (lifecycle.mounts > 1) lifecycle.remounts += 1
}

export function noteDispose(): void {
  lifecycle.disposes += 1
}

export function publishSnapshot(
  value: Omit<ThreeDCraftSnapshot, 'schema' | 'version' | 'lifecycle'>,
): ThreeDCraftSnapshot {
  const snapshot: ThreeDCraftSnapshot = Object.freeze({
    schema: '3d-craft.web-observability.v1',
    version: '0.1.0',
    ...value,
    lifecycle: Object.freeze({ ...lifecycle }),
  })
  current = snapshot
  if (import.meta.env.DEV || import.meta.env.MODE === 'test') {
    window.__THREE_D_CRAFT__ = snapshot
  }
  return snapshot
}

export function currentSnapshot(): ThreeDCraftSnapshot | undefined {
  return current
}
