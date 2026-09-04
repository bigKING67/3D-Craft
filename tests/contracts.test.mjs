import assert from 'node:assert/strict'
import Ajv2020 from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

test('all four schemas validate complete contracts and reject nested drift', async () => {
  const names = ['run.v1.schema.json', 'scene.v1.schema.json', 'asset.v1.schema.json', 'validation.v1.schema.json']
  const schemas = await Promise.all(names.map(async (name) => JSON.parse(await readFile(path.join(root, 'skills/3d-craft/schemas', name), 'utf8'))))
  assert.equal(new Set(schemas.map((schema) => schema.$id)).size, 4)
  const ajv = new Ajv2020({ allErrors: true, strict: true })
  addFormats(ajv)
  for (const schema of schemas) {
    assert.equal(schema.additionalProperties, false)
    ajv.addSchema(schema)
  }
  const scene = JSON.parse(await readFile(path.join(root, 'evals/coffee-grinder/scene.json'), 'utf8'))
  const validateScene = ajv.getSchema('https://3d-craft.local/schemas/scene.v1.schema.json')
  assert.equal(validateScene(scene), true, JSON.stringify(validateScene.errors))

  const hash = 'a'.repeat(64)
  const route = {
    schema: '3d-craft.route.v1',
    target: 'blender',
    intent: 'validate',
    profile: 'prop',
    quality_tier: 'draft',
    authoring_mode: 'native',
    evidence_level: 'static',
    selected_references: ['authority-and-evidence.md', 'repair-and-security.md', 'blender-production.md'],
    required_capabilities: ['blender.version', 'blender.inspect'],
    hard_gates: ['authority', 'reproduction', 'scene_integrity', 'identity', 'delivery'],
    unsupported_in_v0_1: ['reference-image-reconstruction', 'character-production', 'complex-animation-and-simulation', 'games', 'webgpu', 'external-ai-3d-generation'],
  }
  const run = {
    schema: '3d-craft.run.v1',
    run_id: 'fixture-0001',
    project_key: 'fixture',
    created_at: '2026-09-02T00:00:00Z',
    input_hashes: { scene_contract: hash },
    route,
    capabilities: { 'blender.version': 'available', 'blender.inspect': 'available' },
    versions: { '3d-craft': '0.1.0' },
    stages: route.hard_gates.map((id) => ({ id, status: 'pending' })),
    repairs: [],
    evidence: [{ kind: 'blend-inspection', path: 'evidence/blend-inspection.json' }],
    unverified: [],
  }
  const asset = {
    schema: '3d-craft.asset.v1',
    authority: 'native',
    source: { path: '/tmp/source.blend', sha256: hash, bytes: 1 },
    derived: [{ path: '/tmp/asset.blend', sha256: hash, bytes: 1 }],
    tool_versions: { blender: '5.2.1' },
    licenses: [{ subject: 'fixture', license: 'MIT', source: 'original' }],
    gltf_summary: { nodes: 0, meshes: 0, primitives: 0, materials: 0, textures: 0, animations: 0, triangles: 0, extensions: [] },
  }
  const validation = {
    schema: '3d-craft.validation.v1',
    candidate_sha256: hash,
    status: 'PASS',
    gates: [{ id: 'authority', status: 'PASS', evidence: ['run.json'], note: 'bound' }],
    evidence: ['run.json'],
    issues: [],
    repairs: [],
    delivery: { files: [{ path: '/tmp/asset.blend', sha256: hash, bytes: 1 }], commands: ['validate'], unverified: [] },
  }
  for (const [id, document] of [
    ['https://3d-craft.local/schemas/run.v1.schema.json', run],
    ['https://3d-craft.local/schemas/asset.v1.schema.json', asset],
    ['https://3d-craft.local/schemas/validation.v1.schema.json', validation],
  ]) {
    const validate = ajv.getSchema(id)
    assert.equal(validate(document), true, JSON.stringify(validate.errors))
  }

  const driftedScene = structuredClone(scene)
  driftedScene.runtime.credential = 'must-not-be-accepted'
  assert.equal(validateScene(driftedScene), false)

  const customOrigin = structuredClone(scene)
  customOrigin.origin_policy = 'declared-custom'
  assert.equal(validateScene(customOrigin), false)
  customOrigin.framing_center = [0, 0, 0.16]
  assert.equal(validateScene(customOrigin), true, JSON.stringify(validateScene.errors))
})

test('viewer pins the validated R3F stack, splits dependency chunks, and keeps observability development-only', async () => {
  const viewer = path.join(root, 'skills/3d-craft/assets/r3f-viewer')
  const packageJson = JSON.parse(await readFile(path.join(viewer, 'package.json'), 'utf8'))
  const packageLock = JSON.parse(await readFile(path.join(viewer, 'package-lock.json'), 'utf8'))
  assert.equal(packageJson.dependencies.react, '19.2.8')
  assert.equal(packageJson.dependencies['@react-three/fiber'], '9.7.0')
  assert.equal(packageJson.dependencies['@react-three/drei'], '10.7.8')
  assert.equal(packageJson.dependencies.three, '0.185.1')
  assert.deepEqual(packageLock.packages[''].dependencies, packageJson.dependencies)
  assert.deepEqual(packageLock.packages[''].devDependencies, packageJson.devDependencies)
  const observability = await readFile(path.join(viewer, 'src/observability.ts'), 'utf8')
  const assetScene = await readFile(path.join(viewer, 'src/AssetScene.tsx'), 'utf8')
  const app = await readFile(path.join(viewer, 'src/App.tsx'), 'utf8')
  const viteConfig = await readFile(path.join(viewer, 'vite.config.ts'), 'utf8')
  const runtimeQa = await readFile(path.join(root, 'skills/3d-craft/references/web3d-runtime-qa.md'), 'utf8')
  assert.match(observability, /import\.meta\.env\.DEV/)
  assert.match(observability, /Object\.freeze/)
  assert.match(assetScene, /DISPLAY_MAX_DIMENSION_METERS/)
  assert.match(assetScene, /maximumDimension <= 0/)
  assert.match(assetScene, /displayRoot\.scale\.setScalar/)
  assert.match(assetScene, /const disposedTextures = new Set<Texture>/)
  assert.match(assetScene, /loadedRoot = displayRoot\s+noteMount\(\)/)
  assert.match(assetScene, /nodeNames: Object\.freeze/)
  assert.match(assetScene, /materialNames: Object\.freeze/)
  assert.match(app, /motion.*reduce/)
  assert.match(app, /forcedReducedMotion \|\| media\.matches/)
  assert.match(app, /import\('\.\/AssetScene'\)/)
  assert.match(app, /The 3D runtime could not be loaded/)
  assert.match(viteConfig, /chunkSizeWarningLimit: 800/)
  for (const chunk of ['react-runtime', 'three-runtime', 'r3f-runtime', 'vendor']) {
    assert.match(viteConfig, new RegExp(`name: '${chunk}'`))
  }
  assert.match(runtimeQa, /readiness stimulus, not visual acceptance/)
  assert.match(runtimeQa, /visibilityState.*remains `hidden`/)
  assert.match(runtimeQa, /`INVALID SAMPLE`/)
  assert.match(runtimeQa, /absence in production is expected/)
})
