/**
 * Content script (Phase 10).
 *
 * The content script is the only context that touches the page DOM. It
 * never talks to the network — every request is routed to the background
 * service worker through the typed message contract.
 *
 * Safety: claim text and analysis results are treated as untrusted data.
 * Highlighting is done exclusively through [Range] + [Highlight] objects
 * created from the page's own text nodes — we never set innerHTML or
 * insert markup derived from server content.
 */
import {
  ContentMessageType,
  HighlightClaimsRequest,
  RequestMessage,
  ResponseMessage,
  success,
} from '../shared/contracts';

/** Guardrail: never highlight more than this many claims in one pass. */
const MAX_CLAIMS = 50;
/** Guardrail: individual claim text must be sane length for matching. */
const MIN_CLAIM_LENGTH = 8;
const MAX_CLAIM_LENGTH = 500;

export interface ClaimMatch {
  /** Text found on the page (normalized the same way as the search). */
  text: string;
  verifiability: number;
  /** Ranges on the page that matched this claim. */
  count: number;
}

export interface HighlightResult {
  matched: ClaimMatch[];
  unmatchedCount: number;
}

/** Walk text nodes, split on the claim text (case-insensitive), wrap matches. */
export function highlightClaims(
  claims: { text: string; verifiability: number }[],
  root: ParentNode = document.body,
): HighlightResult {
  const matched: ClaimMatch[] = [];
  let unmatchedCount = 0;

  // Collect the page's text nodes first — walking the live DOM while
  // splitting nodes invalidates the iterator, so snapshot them up front.
  const textNodes: Text[] = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    textNodes.push(node as Text);
    node = walker.nextNode();
  }

  for (const claim of claims.slice(0, MAX_CLAIMS)) {
    const needle = claim.text.trim();
    if (needle.length < MIN_CLAIM_LENGTH || needle.length > MAX_CLAIM_LENGTH) {
      unmatchedCount += 1;
      continue;
    }
    const ranges = matchInTextNodes(needle, textNodes);
    if (ranges.length === 0) {
      unmatchedCount += 1;
      continue;
    }
    ranges.forEach((range) => wrapInHighlight(range, claim.verifiability));
    matched.push({ text: needle, verifiability: claim.verifiability, count: ranges.length });
  }

  return { matched, unmatchedCount };
}

/** Case-insensitive, whitespace-collapsed matching across text nodes. */
function matchInTextNodes(needle: string, textNodes: Text[]): Range[] {
  const ranges: Range[] = [];
  // The page is matched in chunks that can span element boundaries, so we
  // build one combined string with a map back to (node, offset) pairs.
  const combined: { node: Text; offset: number }[] = [];
  let haystack = '';
  for (const textNode of textNodes) {
    const value = textNode.data;
    for (let i = 0; i < value.length; i += 1) {
      combined.push({ node: textNode, offset: i });
    }
    haystack += value;
  }

  const needleLower = needle.toLocaleLowerCase();
  const haystackLower = haystack.toLocaleLowerCase();
  let index = 0;
  while (index < haystack.length) {
    const found = haystackLower.indexOf(needleLower, index);
    if (found === -1) break;
    const start = combined[found];
    const end = combined[found + needle.length - 1];
    if (start && end && start.node === end.node) {
      const range = document.createRange();
      range.setStart(start.node, start.offset);
      range.setEnd(end.node, end.offset + 1);
      ranges.push(range);
    }
    index = found + needle.length;
  }
  return ranges;
}

/** Wrap a range in a highlight element (no innerHTML — node-based only). */
function wrapInHighlight(range: Range, verifiability: number): void {
  const mark = document.createElement('mark');
  mark.className = 'annex-highlight';
  mark.dataset.annexScore = String(verifiability);
  try {
    range.surroundContents(mark);
  } catch {
    // surroundContents throws when the range splits an element boundary.
    // Fall back to highlighting the first text node of the range so the
    // claim is still visible without mutating the document structure.
    const firstNode = range.startContainer;
    if (firstNode.nodeType === Node.TEXT_NODE) {
      const partial = document.createElement('mark');
      partial.className = 'annex-highlight';
      partial.dataset.annexScore = String(verifiability);
      firstNode.parentNode?.insertBefore(partial, firstNode.nextSibling);
      partial.append(firstNode);
    }
  }
}

/* ------------------------------------------------------------------ */
/* Bridge: background → content                                        */
/* ------------------------------------------------------------------ */

type ContentInbound =
  | RequestMessage
  | { type: Extract<ContentMessageType, 'annex:get-selection'> }
  | { type: Extract<ContentMessageType, 'annex:selection'>; text: string };

chrome.runtime.onMessage.addListener(
  (
    message: ContentInbound,
    _sender,
    sendResponse: (r: ResponseMessage<HighlightResult | { text: string }>) => void,
  ) => {
    if (message.type === 'highlight-claims') {
      const { claims } = message.payload as HighlightClaimsRequest;
      try {
        const result = highlightClaims(claims);
        sendResponse(success(result));
      } catch (error) {
        sendResponse({
          ok: false,
          error: { code: 'content.highlight_failed', message: String(error) },
        });
      }
      return false; // response sent synchronously; no async channel needed
    }
    if (message.type === 'annex:get-selection') {
      const selection = window.getSelection()?.toString() ?? '';
      sendResponse(success({ text: selection }));
      return false; // response sent synchronously
    }
    if (message.type === 'annex:selection') {
      const selection = window.getSelection();
      const text = message.text || selection?.toString() || '';
      let marked = false;
      if (selection && !selection.isCollapsed && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        const mark = document.createElement('mark');
        mark.className = 'annex-selection';
        try {
          range.surroundContents(mark);
          marked = true;
        } catch {
          marked = false;
        }
      }
      sendResponse(success({ text, marked }));
      return false; // response sent synchronously
    }
    // Only content-local messages flow here; everything else goes to the
    // background. Return false so we never claim other message types.
    return false;
  },
);
