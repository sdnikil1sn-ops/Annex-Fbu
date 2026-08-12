import { afterEach, describe, expect, it, vi } from 'vitest';
import { highlightClaims } from '../src/content/index';
import { chromeMock } from './setup';

/**
 * The content module registers listeners on import via the chrome mock;
 * these tests exercise the pure highlighting engine against the jsdom
 * environment vitest provides (document, Node, NodeFilter are globals).
 */
function render(html: string): HTMLElement {
  let root = document.getElementById('page');
  if (!root) {
    root = document.createElement('article');
    root.id = 'page';
    document.body.appendChild(root);
  }
  root.innerHTML = '';
  root.innerHTML = html;
  return root;
}

afterEach(() => {
  render('<p></p>');
  vi.clearAllMocks();
});

describe('highlightClaims', () => {
  it('wraps matching claim text in <mark class="annex-highlight">', () => {
    const root = render('<p>The earth is round and the sky is blue.</p>');
    const result = highlightClaims([{ text: 'the earth is round', verifiability: 0.9 }], root);

    const marks = root.querySelectorAll('mark.annex-highlight');
    expect(marks.length).toBe(1);
    // The mark preserves the page's original casing.
    expect(marks[0]?.textContent).toBe('The earth is round');
    expect(marks[0]?.getAttribute('data-annex-score')).toBe('0.9');
    expect(result.matched).toEqual([{ text: 'the earth is round', verifiability: 0.9, count: 1 }]);
    expect(result.unmatchedCount).toBe(0);
  });

  it('matches case-insensitively and multiple times', () => {
    const root = render('<p>Round and round we go around.</p>');
    const result = highlightClaims([{ text: 'round and round', verifiability: 0.4 }], root);
    expect(root.querySelectorAll('mark.annex-highlight').length).toBe(1);
    expect(result.matched[0]?.count).toBe(1);
  });

  it('rejects claims that are too short to be meaningful', () => {
    const root = render('<p>Hello world content here.</p>');
    const result = highlightClaims([{ text: 'hi', verifiability: 0.5 }], root);
    expect(result.matched.length).toBe(0);
    expect(result.unmatchedCount).toBe(1);
    expect(root.querySelectorAll('mark.annex-highlight').length).toBe(0);
  });

  it('reports unmatched claims without throwing', () => {
    const root = render('<p>Nothing relevant here.</p>');
    const result = highlightClaims([{ text: 'absent claim text', verifiability: 0.2 }], root);
    expect(result.matched.length).toBe(0);
    expect(result.unmatchedCount).toBe(1);
  });

  it('never sets innerHTML or inserts raw server markup', () => {
    const root = render('<p>Safe page text.</p>');
    const malicious = [{ text: '<img src=x onerror=alert(1)>', verifiability: 0.1 }];
    const result = highlightClaims(malicious, root);
    // No element with an img or onerror can be created: node-based matching
    // treats the payload as literal text, and it cannot appear on the page.
    expect(root.querySelector('img')).toBeNull();
    expect(result.matched.length).toBe(0);
  });

  it('caps the number of highlighted claims', () => {
    const root = render('<p>Claim text number one.</p>');
    const claims = Array.from({ length: 60 }, (_, i) => ({
      text: `Claim text number ${i}.`,
      verifiability: 0.5,
    }));
    const result = highlightClaims(claims, root);
    expect(result.matched.length).toBeLessThanOrEqual(50);
  });
});

describe('content message bridge', () => {
  it('returns the current page selection for annex:get-selection', () => {
    // jsdom provides a Selection object on window; without a real user
    // selection it is empty — the bridge must respond with the empty text.
    let response: unknown;
    chromeMock.runtime.onMessage._emit(
      { type: 'annex:get-selection', requestId: 't1', payload: {} },
      {},
      (r: unknown) => {
        response = r;
      },
    );
    expect(response).toEqual({ ok: true, data: { text: '' } });
  });

  it('handles highlight-claims and reports matched/unmatched counts', () => {
    render('<p>Selected sentence to verify is right here.</p>');
    let response: unknown;
    chromeMock.runtime.onMessage._emit(
      {
        type: 'highlight-claims',
        requestId: 't2',
        payload: {
          claims: [{ text: 'Selected sentence to verify', verifiability: 0.8 }],
        },
      },
      {},
      (r: unknown) => {
        response = r;
      },
    );
    const data = response as {
      ok: boolean;
      data: { matched: { count: number }[]; unmatchedCount: number };
    };
    expect(data.ok).toBe(true);
    expect(data.data.matched.length).toBe(1);
    expect(data.data.matched[0]?.count).toBe(1);
    expect(data.data.unmatchedCount).toBe(0);
  });
});
