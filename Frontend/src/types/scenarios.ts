export type ScenarioTrack = 'speech' | 'reasoning'
export type ScenarioDifficulty = 'easy' | 'medium' | 'hard' | 'expert'
export type CallerLanguage = 'Hinglish' | 'Hindi' | 'English'

export interface Scenario {
  id: string
  type: string
  difficulty: ScenarioDifficulty
  language: string
  conditions: string[]
  caller: string
  expected: string
  track?: ScenarioTrack
}

export interface ScenarioGenerationRequest {
  agentRole: string
  businessContext: string
  supportedTasks: string[]
  language: CallerLanguage
  scenarioCount: number
  track?: ScenarioTrack
}

export interface ScenarioVoiceAgentContext {
  agent_role: string
  business_context: string
  supported_tasks: string[]
  language: string
}

export interface ScenarioGenerationResponse {
  source: 'backend'
  scenarios: Scenario[]
  benchmarkPath?: string
  benchmarkId?: string
  voiceAgentContext?: ScenarioVoiceAgentContext
}
