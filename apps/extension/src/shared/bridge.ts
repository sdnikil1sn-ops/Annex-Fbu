/**
 * Typed bridge over `chrome.runtime.sendMessage` (Phase 10).
 *
 * Every popup/options request funnels through this one function so the
 * contract types are checked at compile time and errors are normalized
 * into the same envelope every caller handles.
 */
import { MessageType, RequestMessage, ResponseMessage } from './contracts';

let requestCounter = 0;

/** Send a typed message to the background and await the typed reply. */
export function sendMessage<T>(type: MessageType, payload: unknown): Promise<T> {
  const message: RequestMessage = { type, requestId: `req-${++requestCounter}`, payload };
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response: ResponseMessage<T> | undefined) => {
      const lastError = chrome.runtime.lastError;
      if (lastError) {
        reject(new Error(lastError.message ?? 'runtime.lastError'));
        return;
      }
      if (!response) {
        reject(new Error('No response from the background worker.'));
        return;
      }
      if (!response.ok) {
        const error = new Error(response.error.message);
        (error as { code?: string }).code = response.error.code;
        reject(error);
        return;
      }
      resolve(response.data);
    });
  });
}
