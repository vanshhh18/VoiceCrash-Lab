/**
 * Central API client for the VoiceCrashLab backend adapter (api/server.py).
 *
 * The backend URL is configurable via VITE_API_URL (default: local FastAPI
 * server on http://localhost:8000). No secrets are stored in the client;
 * agent tokens are only ever sent to the backend adapter, which owns the
 * HTTP call to the voice agent.
 */
import type { EvaluationRecord } from '../types/evaluation'
import type { Scenario } from '../types/scenarios'

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let detail = `Request failed with HTTP ${response.status}.`
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') detail = body.detail
  } catch {
    // keep default detail
  }
  return new ApiError(response.status, detail)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch (cause) {
    throw new ApiError(0, `Backend at ${API_BASE_URL} is unreachable.`)
  }
  if (!response.ok) throw await parseError(response)
  return (await response.json()) as T
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path)
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/** Maps an on-disk audio path served by the backend to a streamable URL. */
export function audioUrl(path: string): string {
  return `${API_BASE_URL}/api/audio?path=${encodeURIComponent(path)}`
}

export interface BackendFeatures {
  overview_metrics: boolean
  scenario_generation: boolean
  agent_connection_test: boolean
  per_test_execution: boolean
  transcripts: boolean
  latency_metrics: boolean
  llm_fix_suggestions: boolean
}

export interface BackendHealth {
  status: string
  app: string
  version: string
  features: BackendFeatures
}

export async function fetchHealth(): Promise<BackendHealth> {
  return apiGet<BackendHealth>('/api/health')
}

/* ---------------------------------------------------------------------- */
/* Backend data shapes (mirror api/server.py responses)                    */
/* ---------------------------------------------------------------------- */

export interface BenchmarkSummary {
  benchmark_id: string
  agent_role: string
  language: string
  scenario_count: number
  updated_at: string
}

export interface BenchmarkDetail {
  benchmark_id: string
  agent_role: string
  business_context: string
  supported_tasks: string[]
  language: string
  scenario_count: number
  scenario_counts: { speech: number; reasoning: number }
  scenarios: { speech: Scenario[]; reasoning: Scenario[] }
}

/** Mirrors data/manifests/*.json entries produced by audio/build_manifest.py. */
export interface ManifestItem {
  test_id: string
  scenario_id: string
  category: string
  scenario_type: string
  language: string
  condition: 'clean' | 'attacked'
  attack_type: string | null
  attack_level: string | null
  expected: string
  audio_path: string
}

/** Mirrors the in-memory status of POST /api/execute/{id}. */
export interface RunStatus {
  running: boolean
  started_at: string
  finished_at: string | null
  total: number
  completed: number
  passed: number
  failed: number
  per_test: Record<string, string>
}

/** Mirrors an entry of data/results/<id>/agent_responses.json. */
export interface AgentResponseEntry {
  test_id: string
  status: string
  endpoint?: string
  http_status?: number
  agent_name?: string
  response_audio_path?: string
  response_content_type?: string
  response_text?: string
  agent_response?: string
  scenario_id?: string
  category?: string
  attack_type?: string | null
  condition?: string
  audio_path?: string
  error?: string
}

/** Mirrors GET /api/results/{id}. */
export interface ResultsBundle {
  benchmark_id: string
  agent_responses: AgentResponseEntry[]
  evaluation_records: EvaluationRecord[]
}
