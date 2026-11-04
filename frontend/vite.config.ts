import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { cpSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = fileURLToPath(new URL('.', import.meta.url));

// Salin aset Blockly (kursor, ikon) supaya tidak perlu CDN.
function blocklyMedia(): Plugin {
  return {
    name: 'blockly-media',
    writeBundle(options) {
      const src = resolve(here, 'node_modules/blockly/media');
      const out = resolve(options.dir ?? 'dist', 'blockly-media');
      if (existsSync(src)) cpSync(src, out, { recursive: true });
    },
  };
}

const backend = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
  base: './',
  plugins: [react(), blocklyMedia()],
  server: {
    proxy: {
      '/api': backend,
      '/ws': { target: backend.replace(/^http/, 'ws'), ws: true },
    },
  },
  build: {
    chunkSizeWarningLimit: 2000,
  },
});
