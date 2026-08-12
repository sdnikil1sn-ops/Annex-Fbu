/**
 * Vitest setup: jest-dom matchers + a minimal chrome.* mock.
 *
 * The chrome mock is a test double that records listeners and lets tests
 * drive responses; production behavior lives behind the real browser.
 */
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

type Listener = (...args: unknown[]) => unknown;

function makeEvent() {
  const listeners: Listener[] = [];
  return {
    addListener: vi.fn((fn: Listener) => {
      listeners.push(fn);
    }),
    removeListener: vi.fn((fn: Listener) => {
      const index = listeners.indexOf(fn);
      if (index !== -1) listeners.splice(index, 1);
    }),
    /** Test helper: invoke registered listeners with args. */
    _emit: (...args: unknown[]) => listeners.forEach((fn) => fn(...args)),
    _listeners: listeners,
  };
}

const runtimeEvent = makeEvent();
const contextMenusEvent = makeEvent();
const installedEvent = makeEvent();

const chromeMock = {
  runtime: {
    onMessage: runtimeEvent,
    onInstalled: installedEvent,
    sendMessage: vi.fn(),
    lastError: undefined,
  },
  contextMenus: {
    create: vi.fn(),
    onClicked: contextMenusEvent,
  },
  tabs: {
    query: vi.fn(),
    sendMessage: vi.fn(),
  },
  storage: {
    sync: {
      get: vi.fn(async () => ({})),
      set: vi.fn(),
    },
  },
};

(globalThis as Record<string, unknown>).chrome = chromeMock;

export { chromeMock, contextMenusEvent, runtimeEvent, installedEvent };
