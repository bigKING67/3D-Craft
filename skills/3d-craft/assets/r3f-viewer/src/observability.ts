export type ViewerStatus = 'loading' | 'ready' | 'context-lost' | 'restoring' | 'error'
export type ContextStatus = 'healthy' | 'lost' | 'restoring'

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
  readonly lifecycle: Readonly<{
    mounts: number
    remounts: number
    disposes: number
    context: Readonly<{
      status: ContextStatus
      losses: number
      restores: number
      test_supported: boolean
      last_lost_at_ms: number | null
      last_restored_at_ms: number | null
    }>
  }>
  readonly error: Readonly<{ message: string }> | null
}

declare global {
  interface Window {
    __THREE_D_CRAFT__?: ThreeDCraftSnapshot
  }
}

const lifecycle = {
  mounts: 0,
  remounts: 0,
  disposes: 0,
  context: {
    status: 'healthy' as ContextStatus,
    losses: 0,
    restores: 0,
    test_supported: false,
    last_lost_at_ms: null as number | null,
    last_restored_at_ms: null as number | null,
  },
}
let current: ThreeDCraftSnapshot | undefined

function frozenLifecycle(): ThreeDCraftSnapshot['lifecycle'] {
  return Object.freeze({
    mounts: lifecycle.mounts,
    remounts: lifecycle.remounts,
    disposes: lifecycle.disposes,
    context: Object.freeze({ ...lifecycle.context }),
  })
}

function expose(snapshot: ThreeDCraftSnapshot): void {
  current = snapshot
  if (import.meta.env.DEV || import.meta.env.MODE === 'test') {
    window.__THREE_D_CRAFT__ = snapshot
  }
}

function republishLifecycle(status?: ViewerStatus): void {
  if (!current) return
  expose(Object.freeze({
    ...current,
    ...(status ? { status } : {}),
    lifecycle: frozenLifecycle(),
  }))
}

export function noteMount(): void {
  lifecycle.mounts += 1
  if (lifecycle.mounts > 1) lifecycle.remounts += 1
}

export function noteDispose(): void {
  lifecycle.disposes += 1
}

export function noteContextTestSupport(supported: boolean): void {
  lifecycle.context.test_supported = supported
  republishLifecycle()
}

export function noteContextLost(now = performance.now()): void {
  lifecycle.context.status = 'lost'
  lifecycle.context.losses += 1
  lifecycle.context.last_lost_at_ms = now
  republishLifecycle('context-lost')
}

export function noteContextRestoring(now = performance.now()): void {
  lifecycle.context.status = 'restoring'
  lifecycle.context.restores += 1
  lifecycle.context.last_restored_at_ms = now
  republishLifecycle('restoring')
}

export function noteContextHealthy(resumedStatus: ViewerStatus): void {
  lifecycle.context.status = 'healthy'
  republishLifecycle(resumedStatus)
}

export function publishSnapshot(
  value: Omit<ThreeDCraftSnapshot, 'schema' | 'version' | 'lifecycle'>,
): ThreeDCraftSnapshot {
  const snapshot: ThreeDCraftSnapshot = Object.freeze({
    schema: '3d-craft.web-observability.v1',
    version: '0.1.0',
    ...value,
    lifecycle: frozenLifecycle(),
  })
  expose(snapshot)
  return snapshot
}

export function currentSnapshot(): ThreeDCraftSnapshot | undefined {
  return current
}
