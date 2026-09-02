import { OrbitControls } from '@react-three/drei'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Box3,
  Color,
  Group,
  MathUtils,
  Mesh,
  MeshStandardMaterial,
  Object3D,
  SRGBColorSpace,
  Texture,
  Vector3,
  WebGLRenderer,
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import {
  currentSnapshot,
  noteDispose,
  noteMount,
  publishSnapshot,
  type ViewerStatus,
} from './observability'

interface SceneFacts {
  objects: number
  meshes: number
  materials: number
  dimensions: [number, number, number]
}

interface AssetSceneProps {
  assetUrl: string
  assetSha256: string
  reducedMotion: boolean
  onStatus: (status: ViewerStatus, detail?: string) => void
  onFacts: (facts: SceneFacts) => void
}

function disposeObject(root: Object3D): void {
  const disposedMaterials = new Set<MeshStandardMaterial>()
  root.traverse((child) => {
    if (!(child instanceof Mesh)) return
    child.geometry.dispose()
    const materials = Array.isArray(child.material) ? child.material : [child.material]
    for (const material of materials) {
      if (disposedMaterials.has(material as MeshStandardMaterial)) continue
      disposedMaterials.add(material as MeshStandardMaterial)
      for (const value of Object.values(material)) {
        if (value && typeof value === 'object' && 'isTexture' in value && (value as Texture).isTexture) {
          ;(value as Texture).dispose()
        }
      }
      material.dispose()
    }
  })
  noteDispose()
}

function LoadedAsset({ assetUrl, onStatus, onFacts }: Pick<AssetSceneProps, 'assetUrl' | 'onStatus' | 'onFacts'>) {
  const [root, setRoot] = useState<Group | null>(null)

  useEffect(() => {
    let cancelled = false
    let loadedRoot: Group | null = null
    onStatus('loading')
    const loader = new GLTFLoader()
    loader.load(
      assetUrl,
      (gltf) => {
        if (cancelled) {
          disposeObject(gltf.scene)
          return
        }
        const bounds = new Box3().setFromObject(gltf.scene)
        const size = bounds.getSize(new Vector3())
        const center = bounds.getCenter(new Vector3())
        gltf.scene.position.sub(center)
        gltf.scene.position.y += size.y / 2
        let objects = 0
        let meshes = 0
        const materials = new Set()
        gltf.scene.traverse((child) => {
          objects += 1
          if (child instanceof Mesh) {
            meshes += 1
            child.castShadow = false
            child.receiveShadow = false
            const owned = Array.isArray(child.material) ? child.material : [child.material]
            owned.forEach((material) => materials.add(material))
          }
        })
        onFacts({
          objects,
          meshes,
          materials: materials.size,
          dimensions: [size.x, size.z, size.y],
        })
        loadedRoot = gltf.scene
        setRoot(loadedRoot)
        onStatus('ready')
      },
      undefined,
      (error) => onStatus('error', error instanceof Error ? error.message : String(error)),
    )
    return () => {
      cancelled = true
      if (loadedRoot) disposeObject(loadedRoot)
    }
  }, [assetUrl, onFacts, onStatus])

  return root ? <primitive object={root} /> : null
}

function RuntimeProbe({ assetUrl, assetSha256, facts, status, error }: {
  assetUrl: string
  assetSha256: string
  facts: SceneFacts
  status: ViewerStatus
  error: string
}) {
  const { camera, gl, size, viewport } = useThree()
  const frames = useRef<number[]>([])
  const lastFrame = useRef<number | null>(null)
  const frameCount = useRef(currentSnapshot()?.raf.frame_count ?? 0)
  const lastPublish = useRef(0)

  useFrame(() => {
    const now = performance.now()
    frameCount.current += 1
    if (lastFrame.current !== null) {
      frames.current.push(now - lastFrame.current)
      if (frames.current.length > 720) frames.current.shift()
    }
    lastFrame.current = now
    if (now - lastPublish.current < 250) return
    lastPublish.current = now
    const sorted = [...frames.current].sort((a, b) => a - b)
    const percentile = (fraction: number) => sorted.length ? sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * fraction))] : null
    publishSnapshot({
      status,
      asset: Object.freeze({ url: assetUrl, sha256: assetSha256 }),
      viewport: Object.freeze({ width: size.width, height: size.height, dpr: viewport.dpr }),
      scene: Object.freeze({
        ...facts,
        dimensions: Object.freeze([...facts.dimensions]) as unknown as [number, number, number],
        camera_position: Object.freeze(camera.position.toArray()) as unknown as [number, number, number],
      }),
      renderer: Object.freeze({
        calls: gl.info.render.calls,
        triangles: gl.info.render.triangles,
        geometries: gl.info.memory.geometries,
        textures: gl.info.memory.textures,
      }),
      raf: Object.freeze({
        status: 'running',
        frame_count: frameCount.current,
        last_frame_at_ms: now,
        frame_p50_ms: percentile(0.5),
        frame_p95_ms: percentile(0.95),
      }),
      error: error ? Object.freeze({ message: error }) : null,
    })
  })
  return null
}

export function AssetScene({ assetUrl, assetSha256, reducedMotion, onStatus, onFacts }: AssetSceneProps) {
  const controls = useRef<OrbitControlsImpl>(null)
  const [status, setStatus] = useState<ViewerStatus>('loading')
  const [error, setError] = useState('')
  const [facts, setFacts] = useState<SceneFacts>({ objects: 0, meshes: 0, materials: 0, dimensions: [0, 0, 0] })
  const callbacks = useMemo(() => ({
    status: (next: ViewerStatus, detail = '') => {
      setStatus(next)
      setError(detail)
      onStatus(next, detail)
    },
    facts: (next: SceneFacts) => {
      setFacts(next)
      onFacts(next)
    },
  }), [onFacts, onStatus])

  useEffect(() => {
    noteMount()
    const reset = () => controls.current?.reset()
    window.addEventListener('3d-craft:reset-camera', reset)
    return () => window.removeEventListener('3d-craft:reset-camera', reset)
  }, [])

  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [0.48, 0.34, 0.56], fov: 32, near: 0.01, far: 100 }}
      gl={(parameters) => {
        const renderer = new WebGLRenderer({ ...parameters, antialias: true, powerPreference: 'high-performance' })
        renderer.outputColorSpace = SRGBColorSpace
        renderer.setClearColor(new Color('#e9e7e1'))
        return renderer
      }}
    >
      <ambientLight intensity={1.25} />
      <directionalLight position={[1.8, 2.4, 1.2]} intensity={3.2} />
      <directionalLight position={[-1.2, 0.8, -1.4]} intensity={1.1} />
      <group rotation={[0, MathUtils.degToRad(18), 0]}>
        <LoadedAsset assetUrl={assetUrl} onStatus={callbacks.status} onFacts={callbacks.facts} />
      </group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.002, 0]}>
        <planeGeometry args={[3, 3]} />
        <meshStandardMaterial color="#dedcd5" roughness={0.96} />
      </mesh>
      <gridHelper args={[2.4, 24, '#b8b7b0', '#d2d0c9']} position={[0, 0.0005, 0]} />
      <OrbitControls
        ref={controls}
        makeDefault
        enableDamping={!reducedMotion}
        dampingFactor={0.07}
        autoRotate={!reducedMotion && status === 'ready'}
        autoRotateSpeed={0.35}
        minDistance={0.35}
        maxDistance={1.8}
        minPolarAngle={Math.PI * 0.18}
        maxPolarAngle={Math.PI * 0.54}
        target={[0, 0.15, 0]}
      />
      <RuntimeProbe assetUrl={assetUrl} assetSha256={assetSha256} facts={facts} status={status} error={error} />
    </Canvas>
  )
}
