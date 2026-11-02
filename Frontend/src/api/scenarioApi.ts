import type { Scenario, ScenarioGenerationRequest, ScenarioGenerationResponse } from '../types/scenarios'
import { apiPost } from './client'

/**
 * Calls the real pipeline generation chain exposed by the FastAPI adapter
 * (api/server.py POST /api/generate -> app.run_pipeline.run_pipeline).
 */
export class BackendNotConnectedError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'BackendNotConnectedError'
  }
}

const SAMPLE_SCENARIOS: Scenario[] = [
  {
    id: 'scenario_1',
    type: 'wrong_number',
    difficulty: 'medium',
    language: 'Hinglish',
    conditions: ['identity_confusion'],
    caller: 'Hello, kya yahan Rahul bol raha hai? Meri delivery Monday ko kahan pahunchi hai?',
    expected: 'Agent should verify identity before sharing any order details.',
  },
  {
    id: 'scenario_2',
    type: 'changing_request',
    difficulty: 'hard',
    language: 'Hinglish',
    conditions: ['request_change'],
    caller: 'Delivery Monday ko chahiye. Actually nahi, Wednesday better hai.',
    expected: "Agent should acknowledge the correction and use Wednesday as the confirmed date.",
  },
  {
    id: 'scenario_3',
    type: 'background_noise',
    difficulty: 'hard',
    language: 'Hindi',
    conditions: ['background_noise', 'partial_transcription'],
    caller: 'Meri delivery Monday ko kar do.',
    expected: 'Agent should still understand the request despite noise, or ask for clarification.',
  },
  {
    id: 'scenario_4',
    type: 'interruption',
    difficulty: 'hard',
    language: 'Hindi',
    conditions: ['request_change'],
    caller: "Actually meri delivery Monday ko... nahi, Tuesday ko kar do.",
    expected: 'Agent should use the final instruction: Tuesday, not Monday.',
  },
  {
    id: 'scenario_5',
    type: 'mumbling',
    difficulty: 'hard',
    language: 'Hindi',
    conditions: ['incomplete_information'],
    caller: 'Umm... woh... delivery... Monday...',
    expected: 'Agent should ask a concise clarification question instead of guessing.',
  },
]

export function fetchSampleScenarios(): Scenario[] {
  return SAMPLE_SCENARIOS
}

export async function generateScenarios(
  request: ScenarioGenerationRequest,
): Promise<ScenarioGenerationResponse> {
  let result
  try {
    result = await apiPost<{
      scenarios: { speech: Scenario[]; reasoning: Scenario[] }
      voice_agent_context: {
        agent_role: string
        business_context: string
        supported_tasks: string[]
        language: string
      }
    }>('/api/generate', {
      agent_role: request.agentRole,
      business_context: request.businessContext,
      supported_tasks: request.supportedTasks,
      language: request.language,
      scenario_count: request.scenarioCount,
    })
  } catch (error) {
    if (error instanceof Error && !('status' in error)) {
      throw new BackendNotConnectedError(
        'The VoiceCrashLab API is not running. Start it with: venv\\Scripts\\python -m uvicorn api.server:app --port 8000',
      )
    }
    throw error
  }

  const speech = (result.scenarios?.speech ?? []) as Scenario[]
  const reasoning = (result.scenarios?.reasoning ?? []) as Scenario[]
  const scenarios: Scenario[] = [
    ...speech.map((s) => ({ ...s, track: s.track ?? ('speech' as const) })),
    ...reasoning.map((s) => ({ ...s, track: s.track ?? ('reasoning' as const) })),
  ]
  return {
    source: 'backend',
    scenarios,
    voiceAgentContext: result.voice_agent_context,
  }
}
