/**
 * Real failure reports (api/server.py GET /api/results/{id} ->
 * data/results/<id>/evaluation_results.json, produced by the dashboard-
 * equivalent evaluation loop in api/server.py).
 */
import { apiGet } from './client'
import type { EvaluationRecord, FailureCategory } from '../types/evaluation'

/**
 * Severity derives from evaluator/crash_score.py CATEGORY_SCORES weights.
 * Categories without a weight (SAFETY_FAILURE, AGENT_REQUEST_FAILURE,
 * EVALUATION_ERROR) are surfaced as critical/major by the judge but have no
 * crash-score weight, so they are labelled accordingly.
 */
export const CRASH_SCORE_WEIGHTS: Partial<Record<FailureCategory, number>> = {
  STT_FAILURE: 40,
  INTENT_MISUNDERSTANDING: 30,
  CONTEXT_FAILURE: 30,
  CLARIFICATION_FAILURE: 30,
  IDENTITY_FAILURE: 30,
  EMPATHY_FAILURE: 30,
  UNKNOWN_FAILURE: 20,
}

export type ReportSeverity = 'critical' | 'major' | 'minor' | 'unweighted'

export function severityFor(category: string): ReportSeverity {
  const weight = CRASH_SCORE_WEIGHTS[category as FailureCategory]
  if (weight === 40) return 'critical'
  if (weight === 30) return 'major'
  if (weight === 20) return 'minor'
  return category === 'SAFETY_FAILURE' ? 'critical' : 'unweighted'
}

export const SEVERITY_ORDER: ReportSeverity[] = ['critical', 'major', 'minor', 'unweighted']

export interface FailureReport {
  test_id: string
  scenario_id: string
  scenario_type: string
  attack_type: string | null
  category: string
  severity: ReportSeverity
  agent_response: string
  caller_transcript: string
  expected: string
  actual: string
  reason: string
  suggestedFix: string | null
  example_response: string | null
  status: string
  evaluated_at: string
}

export function toReport(record: EvaluationRecord): FailureReport {
  const category = record.evaluation?.category ?? (record.status === 'failed' ? 'AGENT_REQUEST_FAILURE' : 'EVALUATION_ERROR')
  return {
    test_id: record.test_id,
    scenario_id: record.scenario_id,
    scenario_type: record.scenario_type,
    attack_type: record.attack_type,
    category,
    severity: severityFor(category),
    agent_response: record.agent_response || record.evaluation?.reason || 'No response received.',
    caller_transcript: record.caller_transcript ?? '',
    expected: record.expected,
    actual: record.agent_response || record.evaluation?.reason || 'No response received.',
    reason: record.evaluation?.reason ?? record.error ?? '',
    suggestedFix: record.suggested_fix && record.suggested_fix.length ? record.suggested_fix : null,
    example_response: record.example_response ?? null,
    status: record.status,
    evaluated_at: record.evaluated_at,
  }
}

export function failureReportsFromRecords(records: EvaluationRecord[]): FailureReport[] {
  return records.filter((r) => r.evaluation?.passed !== true).map(toReport)
}

export function evaluationRecords(benchmarkId: string): Promise<{ evaluation_records: EvaluationRecord[] }> {
  return apiGet(`/api/results/${encodeURIComponent(benchmarkId)}`)
}
