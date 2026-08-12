/**
 * Analysis domain types (ADR-0002 / ADR-0008).
 *
 * Shapes mirror the backend OpenAPI contract: the report carries a
 * `summary` and claims with `text` + numeric `verifiability`; the
 * analysis carries the lifecycle state machine values.
 */
export type AnalysisInputType = 'text' | 'url' | 'image';
export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ClaimItem {
  text: string;
  /** Verifiability in `[0, 1]` (1 = fully verifiable). */
  verifiability: number;
}

export interface AnalysisReport {
  summary: string;
  claims: ClaimItem[];
}

export interface Analysis {
  id: string;
  input_type: AnalysisInputType;
  status: AnalysisStatus;
  locale: string;
  failure_reason: string | null;
  report: AnalysisReport | null;
  created_at: string;
  completed_at: string | null;
}

/** Whether the analysis state machine has reached a terminal state. */
export function isTerminal(status: AnalysisStatus): boolean {
  return status === 'completed' || status === 'failed';
}

/** Overall credibility score: the mean claim verifiability (0..1). */
export function credibilityScore(report: AnalysisReport): number {
  if (report.claims.length === 0) return 0;
  const total = report.claims.reduce((sum, claim) => sum + claim.verifiability, 0);
  return total / report.claims.length;
}
