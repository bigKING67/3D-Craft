import os from 'node:os'
import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  cacheDir: path.join(os.tmpdir(), '3d-craft-vite-cache'),
  plugins: [react()],
  build: {
    outDir: process.env.VITE_OUT_DIR || path.join(os.tmpdir(), '3d-craft-viewer-dist'),
    emptyOutDir: true,
  },
  server: {
    host: '127.0.0.1',
    port: 41767,
    strictPort: true,
  },
  preview: {
    host: '127.0.0.1',
    port: 41767,
    strictPort: true,
  },
})
