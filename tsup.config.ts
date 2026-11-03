import { defineConfig } from 'tsup'

export default defineConfig({
  entry: { bin: 'bin/english.ts' },
  format: ['esm'],
  target: 'node18',
  outDir: 'dist',
  clean: true,
  splitting: false,
  banner: { js: '#!/usr/bin/env node' }
})
