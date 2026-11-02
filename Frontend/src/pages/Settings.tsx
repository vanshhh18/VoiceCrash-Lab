import { useEffect, useState } from 'react'
import { PageSection, PageShell } from '../components/layout/PageShell'
import { Badge, Button, Card, CardTitle, StatusIndicator } from '../components/ui'

const STORAGE_KEY = 'vcl-settings'

interface StoredSettings {
  sttProvider: 'groq' | 'whisper' | 'prisma'
  ttsProvider: 'timbre' | 'edge'
  language: 'Hinglish' | 'Hindi' | 'English'
  ttsVoice: string
  scenarioModel: string
  judgeModel: string
  sttModel: string
  reduceMotion: boolean
  showHelperText: boolean
}

const DEFAULTS: StoredSettings = {
  sttProvider: 'groq',
  ttsProvider: 'timbre',
  language: 'Hinglish',
  ttsVoice: 'hi-IN-SwaraNeural',
  scenarioModel: 'openai/gpt-oss-120b',
  judgeModel: 'openai/gpt-oss-120b',
  sttModel: 'whisper-large-v3-turbo',
  reduceMotion: false,
  showHelperText: true,
}

function loadSettings(): StoredSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULTS
    return { ...DEFAULTS, ...(JSON.parse(raw) as Partial<StoredSettings>) }
  } catch {
    return DEFAULTS
  }
}

/**
 * Values mirror backend environment defaults documented in .env.example and the
 * code (audio/stt/router.py, evaluator/groq_judge.py, dashboard voice default).
 * Changes persist to localStorage in this browser ONLY — they do not modify the
 * backend .env, and they are not sent to any server.
 */
export default function Settings() {
  const [initial] = useState(loadSettings)
  const [sttProvider, setSttProvider] = useState(initial.sttProvider)
  const [ttsProvider, setTtsProvider] = useState(initial.ttsProvider)
  const [language, setLanguage] = useState(initial.language)
  const [ttsVoice, setTtsVoice] = useState(initial.ttsVoice)
  const [scenarioModel, setScenarioModel] = useState(initial.scenarioModel)
  const [judgeModel, setJudgeModel] = useState(initial.judgeModel)
  const [sttModel, setSttModel] = useState(initial.sttModel)
  const [reduceMotion, setReduceMotion] = useState(initial.reduceMotion)
  const [showHelperText, setShowHelperText] = useState(initial.showHelperText)

  useEffect(() => {
    const settings: StoredSettings = {
      sttProvider,
      ttsProvider,
      language,
      ttsVoice,
      scenarioModel,
      judgeModel,
      sttModel,
      reduceMotion,
      showHelperText,
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    } catch {
      // Storage unavailable (e.g. private mode); settings stay in memory.
    }
  }, [sttProvider, ttsProvider, language, ttsVoice, scenarioModel, judgeModel, sttModel, reduceMotion, showHelperText])

  return (
    <PageShell>
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-3 rounded-lg border border-warn/40 bg-warn/10 px-4 py-2.5">
          <Badge tone="red">Local UI only</Badge>
          <p className="text-xs text-warn">
            These settings mirror backend environment defaults and persist to this browser's local
            storage only. They do not change the Python backend (.env, STT routing, or the judge
            model) and are never sent to a server.
          </p>
        </div>

        <Card>
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle>Agent connection</CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                Endpoint, authentication, and multipart fields are configured in the connect flow or
                via backend environment defaults (VOICE_AGENT_*).
              </p>
            </div>
            <StatusIndicator status="offline" label="Not configured" />
          </div>
        </Card>

        <PageSection title="Providers">
          <Card className="flex flex-col gap-4">
            <OptionGroup
              label="STT provider"
              hint="Mirrors STT_PROVIDER: audio/stt/router.py supports groq, whisper, prisma."
            >
              <div className="flex gap-2">
                {(['groq', 'whisper', 'prisma'] as const).map((p) => (
                  <Button
                    key={p}
                    size="sm"
                    variant={sttProvider === p ? 'primary' : 'secondary'}
                    onClick={() => setSttProvider(p)}
                  >
                    {p}
                  </Button>
                ))}
              </div>
            </OptionGroup>
            <OptionGroup
              label="STT model"
              hint="Mirrors GROQ_STT_MODEL (used by the Groq/Whisper STT backend)."
            >
              <input
                value={sttModel}
                onChange={(e) => setSttModel(e.target.value)}
                className="w-full rounded-lg border border-line bg-panel-raised px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-signal/60 md:w-80"
              />
            </OptionGroup>
            <OptionGroup
              label="TTS provider"
              hint="Scenario audio uses the project TTS service (timbre) for caller speech."
            >
              <div className="flex gap-2">
                {(['timbre', 'edge'] as const).map((p) => (
                  <Button
                    key={p}
                    size="sm"
                    variant={ttsProvider === p ? 'primary' : 'secondary'}
                    onClick={() => setTtsProvider(p)}
                  >
                    {p}
                  </Button>
                ))}
              </div>
            </OptionGroup>
            <OptionGroup
              label="Default TTS voice"
              hint="Mirrors VOICECRASHLAB_TTS_VOICE default in .env.example."
            >
              <input
                value={ttsVoice}
                onChange={(e) => setTtsVoice(e.target.value)}
                className="w-full rounded-lg border border-line bg-panel-raised px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-signal/60 md:w-80"
              />
            </OptionGroup>
          </Card>
        </PageSection>

        <PageSection title="Defaults">
          <Card className="flex flex-col gap-4">
            <OptionGroup label="Default caller language" hint="Mirrors the pipeline's language option (Hinglish, Hindi, English).">
              <div className="flex gap-2">
                {(['Hinglish', 'Hindi', 'English'] as const).map((l) => (
                  <Button
                    key={l}
                    size="sm"
                    variant={language === l ? 'primary' : 'secondary'}
                    onClick={() => setLanguage(l)}
                  >
                    {l}
                  </Button>
                ))}
              </div>
            </OptionGroup>
            <OptionGroup label="Scenario model" hint="Mirrors GROQ_SCENARIO_MODEL.">
              <input
                value={scenarioModel}
                onChange={(e) => setScenarioModel(e.target.value)}
                className="w-full rounded-lg border border-line bg-panel-raised px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-signal/60 md:w-80"
              />
            </OptionGroup>
            <OptionGroup label="Judge model" hint="Mirrors GROQ_JUDGE_MODEL (response evaluation).">
              <input
                value={judgeModel}
                onChange={(e) => setJudgeModel(e.target.value)}
                className="w-full rounded-lg border border-line bg-panel-raised px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-signal/60 md:w-80"
              />
            </OptionGroup>
          </Card>
        </PageSection>

        <PageSection title="Interface">
          <Card className="flex flex-col gap-4">
            <ToggleRow
              label="Reduce motion"
              hint="Minimize animated transitions."
              checked={reduceMotion}
              onChange={setReduceMotion}
            />
            <ToggleRow
              label="Helper text"
              hint="Show explanatory captions in forms and panels."
              checked={showHelperText}
              onChange={setShowHelperText}
            />
          </Card>
        </PageSection>

        <Card className="flex flex-col gap-2">
          <CardTitle>API credentials</CardTitle>
          <p className="text-xs text-text-muted">
            Secrets (GROQ_API_KEY, GNANI_API_KEY, agent tokens) live in the backend <span className="font-mono">.env</span> file
            only. This frontend never reads, displays, or stores them.
          </p>
          <Badge tone="green">No secrets exposed in the client</Badge>
        </Card>
      </div>
    </PageShell>
  )
}

function OptionGroup({
  label,
  hint,
  children,
}: {
  label: string
  hint: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-2">
      <div>
        <div className="text-sm font-medium text-text-primary">{label}</div>
        <div className="text-[11px] text-text-muted">{hint}</div>
      </div>
      {children}
    </div>
  )
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string
  hint: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-line bg-panel-raised/60 px-4 py-3">
      <span>
        <span className="block text-sm text-text-primary">{label}</span>
        <span className="block text-xs text-text-muted">{hint}</span>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 accent-signal"
      />
    </label>
  )
}
