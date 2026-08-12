/**
 * ANNEX extension — typed Manifest V3 (single source of truth).
 *
 * The build emits this object as `dist/manifest.json`; nothing in the
 * repository hand-edits a JSON copy. Permissions are least-privilege:
 * only the tabs we highlight, context menus, and storage we read.
 */
export interface AnnexManifest {
  manifest_version: 3;
  name: string;
  version: string;
  description: string;
  action: { default_popup: string; default_title: string };
  background: { service_worker: string };
  options_page: string;
  permissions: string[];
  host_permissions: string[];
  content_scripts: {
    matches: string[];
    js: string[];
    run_at: 'document_idle';
  }[];
  icons: Record<string, string>;
}

/** The extension's declarative identity and entry points. */
export const manifest: AnnexManifest = {
  manifest_version: 3,
  name: 'ANNEX — Learn Before You Believe',
  version: '0.1.0',
  description:
    'Verify claims, sources, and images while you browse with ANNEX media-literacy signals.',
  action: {
    default_popup: 'popup.html',
    default_title: 'Verify with ANNEX',
  },
  background: {
    service_worker: 'background.js',
  },
  options_page: 'options.html',
  permissions: ['contextMenus', 'activeTab', 'storage'],
  // The ANNEX backend API only — never broad web access.
  host_permissions: ['http://localhost:8000/*', 'https://api.annex.app/*'],
  content_scripts: [
    {
      matches: ['<all_urls>'],
      js: ['content.js'],
      run_at: 'document_idle',
    },
  ],
  icons: {
    '16': 'icons/icon16.png',
    '48': 'icons/icon48.png',
    '128': 'icons/icon128.png',
  },
};
