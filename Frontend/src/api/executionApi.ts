/**
 * Real backend execution bridge (api/server.py):
 * - connect agent  -> POST /api/agent/connect   (test_agent_connection)
 * - start a run    -> POST /api/execute/{id}    (manifest test loop in background thread)
 * - poll progress  -> GET  /api/execute/{id}/status
 * - read results   -> GET  /api/results/{id}
 */
import type { AgentResponseEntry, RunStatus } from './client'
import { apiGet, apiPost } from './client'

export interface AgentConfig {
  name: string
  endpoint: string
  token: string
  auth_header: string
  auth_scheme: string
  input_field: string
  response_text_field: string
  response_audio_url_field: string
  timeout: number
}

export const DEFAULT_AGENT_CONFIG: AgentConfig = {
  name: 'Voice Agent',
  endpoint: '',
  token: '',
  auth_header: 'Authorization',
  auth_scheme: 'Bearer',
  input_field: 'audio',
  response_text_field: 'response',
  response_audio_url_field: 'audio_url',
  timeout: 60,
}

export interface AgentConnectionResult {
  status: string
  http_status?: number
  message: string
}

export function connectAgent(config: AgentConfig): Promise<AgentConnectionResult> {
  return apiPost<AgentConnectionResult>('/api/agent/connect', config)
}

/** Mirrors one manifest entry (test to execute). */
export interface ExecutableTest {
  test_id: string
  scenario_id: string
  category: string
  scenario_type: string
  condition: 'clean' | 'attacked'
  attack_type: string | null
  attack_level: string | null
  expected: string
  /** Caller input text lives in the benchmark scenario, not the manifest. */
  caller_input: string | null
  status: 'pending' | 'running' | 'responded' | 'evaluated' | 'failed' | 'evaluation_failed'
  agent_response?: string
  evaluation?: {
    passed: boolean
    category?: string
    reason?: string
  }
  suggested_fix?: string
  response_audio_path?: string
}

export function startRun(benchmarkId: string, config: AgentConfig): Promise<{ status: string; total: number }> {
  return apiPost(`/api/execute/${encodeURIComponent(benchmarkId)}`, {
    ...config,
    benchmark_id: benchmarkId,
  })
}

export function executionStatus(benchmarkId: string): Promise<RunStatus> {
  return apiGet(`/api/execute/${encodeURIComponent(benchmarkId)}/status`)
}

export interface RunResults {
  agent_responses: AgentResponseEntry[]
  evaluation_records: Array<{
    test_id: string
    status: string
    agent_response?: string
    evaluation?: { passed: boolean; category?: string; reason?: string }
    suggested_fix?: string
    example_response?: string
    caller_transcript?: string
  }>
}

export function runResults(benchmarkId: string): Promise<RunResults> {
  return apiGet(`/api/results/${encodeURIComponent(benchmarkId)}`)
}
