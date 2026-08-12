import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { writeFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

import { manifest } from './src/manifest';

/**
 * Emits `dist/manifest.json` from the typed manifest module after build.
 */
function emitManifest(): Plugin {
  return {
    name: 'emit-annex-manifest',
    closeBundle() {
      const outDir = resolve(__dirname, 'dist');
      mkdirSync(outDir, { recursive: true });
      writeFileSync(resolve(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf-8');
    },
  };
}

export default defineConfig({
  plugins: [react(), emitManifest()],
  // Relative asset URLs so the unpacked extension works from any origin
  // (chrome-extension:// resolves ./assets/… to the extension root).
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        // HTML entries at src root emit dist/popup.html and
        // dist/options.html — the exact paths the manifest's
        // action.default_popup / options_page use.
        popup: resolve(__dirname, 'popup.html'),
        options: resolve(__dirname, 'options.html'),
      },
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
      },
    },
  },
});
