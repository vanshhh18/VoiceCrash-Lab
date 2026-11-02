export type FailureCategory =
  | 'STT_FAILURE'
  | 'INTENT_MISUNDERSTANDING'
  | 'CONTEXT_FAILURE'
  | 'CLARIFICATION_FAILURE'
  | 'SAFETY_FAILURE'
  | 'IDENTITY_FAILURE'
  | 'EMPATHY_FAILURE'
  | 'AGENT_REQUEST_FAILURE'
  | 'EVALUATION_ERROR'
  | 'UNKNOWN_FAILURE'

export const CRITICAL_CATEGORIES: FailureCategory[] = ['SAFETY_FAILURE', 'IDENTITY_FAILURE']

export interface EvaluationRecord {
  test_id: string
  scenario_id: string
  category: string
  scenario_type: string
  attack_type: string | null
  condition: string
  expected: string
  agent_response: string
  status: 'evaluated' | 'failed' | 'evaluation_failed'
  evaluation: { passed: boolean; category?: FailureCategory; reason?: string }
  suggested_fix?: string
  example_response?: string
  caller_transcript?: string
  audio_path?: string | null
  evaluated_at: string
  error?: string
}

export interface RunSummary {
  id: string
  label: string
  created_at: string
  totalTests: number
  passed: number
  failed: number
  criticalFailures: number
}

export function aggregate(records: EvaluationRecord[]) {
  const total = records.length
  const passed = records.filter((r) => r.evaluation?.passed === true).length
  const failed = total - passed
  const critical = records.filter(
    (r) =>
      r.evaluation?.passed !== true &&
      CRITICAL_CATEGORIES.includes(r.evaluation?.category as FailureCategory),
  ).length
  return { total, passed, failed, critical, passRate: total ? (passed / total) * 100 : 0 }
}
