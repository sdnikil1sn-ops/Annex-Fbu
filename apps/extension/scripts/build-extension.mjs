/**
 * Builds the non-React entry points (background service worker + content
 * script) as classic IIFE scripts — once per entry, because Rollup's IIFE
 * output format supports a single entry per build. The popup/options
 * React apps are built by the main `vite build` step first.
 */
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
// Invoke the vite CLI directly through the current Node binary — the `npx`
// shim is not reliably spawnable on Windows.
const viteCli = resolve(root, 'node_modules/vite/bin/vite.js');

const entries = ['background', 'content'];
for (const entry of entries) {
  const result = spawnSync(
    process.execPath,
    [viteCli, 'build', '--config', 'vite.extension.config.ts'],
    {
      cwd: root,
      env: { ...process.env, ENTRY: entry },
      stdio: 'inherit',
    },
  );
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}
console.log(`Built ${entries.join(', ')} IIFE bundles.`);
