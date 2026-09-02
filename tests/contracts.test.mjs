import assert from 'node:assert/strict'
import Ajv2020 from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

test('all four schemas have unique ids and closed top-level objects', async () => {
  const names = ['run.v1.schema.json', 'scene.v1.schema.json', 'asset.v1.schema.json', 'validation.v1.schema.json']
  const schemas = await Promise.all(names.map(async (name) => JSON.parse(await readFile(path.join(root, 'skills/3d-craft/schemas', name), 'utf8'))))
  assert.equal(new Set(schemas.map((schema) => schema.$id)).size, 4)
  const ajv = new Ajv2020({ allErrors: true, strict: true })
  addFormats(ajv)
  for (const schema of schemas) {
    assert.equal(schema.additionalProperties, false)
    assert.equal(typeof ajv.compile(schema), 'function')
  }
  const scene = JSON.parse(await readFile(path.join(root, 'evals/coffee-grinder/scene.json'), 'utf8'))
  const validateScene = ajv.getSchema('https://3d-craft.local/schemas/scene.v1.schema.json')
  assert.equal(validateScene(scene), true, JSON.stringify(validateScene.errors))
})

test('viewer pins the validated R3F stack and keeps observability development-only', async () => {
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
  assert.match(observability, /import\.meta\.env\.DEV/)
  assert.match(observability, /Object\.freeze/)
})
