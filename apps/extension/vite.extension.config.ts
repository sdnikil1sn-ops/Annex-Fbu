import { defineConfig, type UserConfig } from 'vite';
import { resolve } from 'node:path';

/**
 * Builds the non-React entry points as classic IIFE scripts (no ESM
 * import statements), which is what Manifest V3 requires for content
 * scripts and supports for service workers. Rollup's IIFE format only
 * allows a single entry per build, so `scripts/build-extension.mjs`
 * invokes this once per entry (background, content) with the `ENTRY`
 * env var. The explicit input key makes the output file name match the
 * manifest's `background.service_worker` / `content_scripts[].js` paths.
 */
export default defineConfig(({ mode }) => {
  const entry = process.env.ENTRY;
  if (!entry) throw new Error('ENTRY env var is required (background | content)');

  const config: UserConfig = {
    build: {
      outDir: 'dist',
      emptyOutDir: false,
      rollupOptions: {
        input: {
          [entry]: resolve(__dirname, `src/${entry}/index.ts`),
        },
        output: {
          format: 'iife',
          entryFileNames: '[name].js',
          assetFileNames: 'assets/[name][extname]',
          inlineDynamicImports: true,
        },
      },
    },
  };
  // Mode is injected by the CLI; used here so `vite build --mode=extension`
  // behaves identically to a plain build.
  void mode;
  return config;
});
