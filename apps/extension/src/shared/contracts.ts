/**
 * Extension message contracts (Phase 10).
 *
 * All cross-context communication (popup ↔ background ↔ content) flows
 * through these typed messages — no ad-hoc strings, no dynamic dispatch.
 * The response envelope is uniform so every caller handles success and
 * failure the same way.
 */
export type MessageType =
  | 'verify'
  | 'fetch-analysis'
  | 'get-locales'
  | 'get-bundle'
  | 'get-selection'
  | 'highlight-claims'
  | 'get-account'
  | 'sign-in'
  | 'sign-out';

/** Content-local messages (background ↔ content, never the API). */
export type ContentMessageType = 'annex:get-selection' | 'annex:selection';

export interface RequestMessage<T = unknown> {
  type: MessageType;
  requestId: string;
  payload: T;
}

export interface VerifyRequest {
  /** The selected or pasted text to analyze. */
  text: string;
  /** The active UI locale. */
  locale: string;
}

export interface FetchAnalysisRequest {
  id: string;
}

export interface GetBundleRequest {
  locale: string;
}

export interface HighlightClaimsRequest {
  claims: { text: string; verifiability: number }[];
}

export type SuccessResponse<T> = { ok: true; data: T };
export type ErrorResponse = { ok: false; error: { code: string; message: string } };
export type ResponseMessage<T> = SuccessResponse<T> | ErrorResponse;

/** Envelope builders shared by every context. */
export function success<T>(data: T): SuccessResponse<T> {
  return { ok: true, data };
}

export function failure(code: string, message: string): ErrorResponse {
  return { ok: false, error: { code, message } };
}
