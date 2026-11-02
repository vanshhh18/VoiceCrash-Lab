import { AnimatePresence, motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import {
  BackendNotConnectedError,
  generateScenarios,
} from '../api/scenarioApi'
import { PageSection, PageShell } from '../components/layout/PageShell'
import { EmptyState, ErrorState, LoadingState } from '../components/states'
import { Badge, Button, Card, StatusIndicator } from '../components/ui'
import type {
  Scenario,
  ScenarioDifficulty,
  ScenarioGenerationRequest,
} from '../types/scenarios'

interface FormState {
  agentRole: string
  businessContext: string
  tasksText: string
  language: 'Hinglish' | 'Hindi' | 'English'
  scenarioCount: number
}

const DIFFICULTY_TONES: Record<ScenarioDifficulty, 'green' | 'cyan' | 'red'> = {
  easy: 'green',
  medium: 'cyan',
  hard: 'red',
  expert: 'red',
}

type DifficultyFilter = 'all' | ScenarioDifficulty

export default function ScenarioLab() {
  const [form, setForm] = useState<FormState>({
    agentRole: '',
    businessContext: '',
    tasksText: '',
    language: 'Hinglish',
    scenarioCount: 5,
  })
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof FormState, string>>>({})
  const [status, setStatus] = useState<'idle' | 'loading' | 'done'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [resultSource, setResultSource] = useState<'backend' | null>(null)
  const [difficultyFilter, setDifficultyFilter] = useState<DifficultyFilter>('all')
  const [selected, setSelected] = useState<Scenario | null>(null)

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((f) => ({ ...f, [key]: value }))
    setFieldErrors((e) => ({ ...e, [key]: undefined }))
  }

  const validate = (): boolean => {
    const errors: Partial<Record<keyof FormState, string>> = {}
    if (!form.agentRole.trim()) errors.agentRole = 'Agent role is required.'
    if (!form.businessContext.trim()) errors.businessContext = 'Business context is required.'
    const tasks = form.tasksText.split('\n').filter((l) => l.trim())
    if (tasks.length === 0) errors.tasksText = 'Add at least one supported task.'
    if (form.scenarioCount < 1 || form.scenarioCount > 20)
      errors.scenarioCount = 'Scenario count must be between 1 and 20.'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleGenerate = async () => {
    if (!validate()) return
    const request: ScenarioGenerationRequest = {
      agentRole: form.agentRole.trim(),
      businessContext: form.businessContext.trim(),
      supportedTasks: form.tasksText.split('\n').filter((l) => l.trim()),
      language: form.language,
      scenarioCount: form.scenarioCount,
    }
    setStatus('loading')
    setError(null)
    setSelected(null)
    try {
      const response = await generateScenarios(request)
      setScenarios(response.scenarios)
      setResultSource(response.source)
      setStatus('done')
    } catch (e) {
      const message =
        e instanceof BackendNotConnectedError
          ? e.message
          : e instanceof Error
            ? e.message
            : String(e)
      setError(message)
      setStatus('idle')
      setScenarios([])
      setResultSource(null)
    }
  }

  const filtered = useMemo(
    () =>
      difficultyFilter === 'all'
        ? scenarios
        : scenarios.filter((s) => s.difficulty === difficultyFilter),
    [scenarios, difficultyFilter],
  )

  return (
    <PageShell>
      <div className="flex flex-col gap-6">
        <Card>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-text-primary">Test suite configuration</h2>
              <p className="text-xs text-text-muted">
                Fields match the pipeline: agent role, business context, supported tasks, caller
                language, and scenarios per track (speech + reasoning).
              </p>
            </div>
            <StatusIndicator status={resultSource === 'backend' ? 'online' : 'idle'} label={resultSource === 'backend' ? 'Generation API connected' : 'Generation API not connected'} />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Agent role / name" error={fieldErrors.agentRole}>
              <input
                className="w-full rounded-lg border border-line bg-panel-raised px-3 py-2 text-sm text-text-primary outline-none transition-colors placeholder:text-text-muted/60 focus:border-signal/60"
                placeholder="e.g. Banking Customer Support Agent"
                value={form.agentRole}
                onChange={(e) => set('agentRole', e.target.value)}
              />
            </Field>
            <Field label="Caller language">
              <select
                className="w-full rounded-lg border border-line bg-panel-raised px-3 py-2 text-sm text-text-primary outline-none focus:border-signal/60"
                value={form.language}
                onChange={(e) => set('language', e.target.value as FormState['language'])}
              >
                {(['Hinglish', 'Hindi', 'English'] as const).map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Business type / description" error={fieldErrors.businessContext} className="md:col-span-2">
              <textarea
                rows={3}
                className="w-full resize-none rounded-lg border border-line bg-panel-raised px-3 py-2 text-sm text-text-primary outline-none placeholder:text-text-muted/60 focus:border-signal/60"
                placeholder="Describe the business, policies, and agent capabilities."
                value={form.businessContext}
                onChange={(e) => set('businessContext', e.target.value)}
              />
            </Field>
            <Field label="Supported tasks (one per line)" error={fieldErrors.tasksText} className="md:col-span-2">
              <textarea
                rows={3}
                className="w-full resize-none rounded-lg border border-line bg-panel-raised px-3 py-2 font-mono text-sm text-text-primary outline-none placeholder:text-text-muted/60 focus:border-signal/60"
                placeholder={'track order\nrequest refund\nreschedule delivery'}
                value={form.tasksText}
                onChange={(e) => set('tasksText', e.target.value)}
              />
            </Field>
            <Field
              label="Scenarios per track (speech & reasoning)"
              error={fieldErrors.scenarioCount}
              hint="Supported: 1–20, mirrors the pipeline limit."
            >
              <input
                type="number"
                min={1}
                max={20}
                className="w-full rounded-lg border border-line bg-panel-raised px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-signal/60"
                value={form.scenarioCount}
                onChange={(e) => set('scenarioCount', Number(e.target.value))}
              />
            </Field>
            <div className="flex items-end">
              <Button onClick={handleGenerate} disabled={status === 'loading'} className="w-full md:w-auto">
                {status === 'loading' ? 'Generating…' : 'Generate test suite'}
              </Button>
            </div>
          </div>
        </Card>

        {status === 'loading' && <LoadingState label="Generating scenarios…" />}
        {error && (
          <ErrorState
            title="Generation unavailable"
            message={error}
            onRetry={handleGenerate}
          />
        )}

        <PageSection title="Generated scenarios">
          {status === 'done' && scenarios.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-text-muted">Difficulty:</span>
              {(['all', 'easy', 'medium', 'hard', 'expert'] as DifficultyFilter[]).map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficultyFilter(d)}
                  className={`rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors ${
                    difficultyFilter === d
                      ? 'border-line bg-signal/10 text-text-primary'
                      : 'border-line bg-panel-raised text-text-muted hover:text-text-primary'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          )}

          {status === 'done' && filtered.length === 0 && scenarios.length > 0 ? (
            <EmptyState
              icon="🔍"
              title="No scenarios match this difficulty"
              description="Try another difficulty filter."
            />
          ) : status === 'done' && filtered.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {filtered.map((s) => (
                <ScenarioCard key={s.id} scenario={s} onOpen={() => setSelected(s)} />
              ))}
            </div>
          ) : status !== 'loading' && status !== 'idle' ? (
            <EmptyState icon="🧬" title="No scenarios yet" description="Configure the suite above and generate." />
          ) : status === 'idle' && !error ? (
            <EmptyState
              icon="🧬"
              title="No scenarios generated yet"
              description="Generate a suite to see adversarial speech and reasoning scenarios here."
            />
          ) : null}
        </PageSection>
      </div>

      <ScenarioDetailDrawer scenario={selected} onClose={() => setSelected(null)} />
    </PageShell>
  )
}

function Field({
  label,
  error,
  hint,
  className = '',
  children,
}: {
  label: string
  error?: string
  hint?: string
  className?: string
  children: React.ReactNode
}) {
  return (
    <label className={`flex flex-col gap-1.5 ${className}`}>
      <span className="text-xs font-medium text-text-primary">{label}</span>
      {children}
      {hint && !error && <span className="text-[11px] text-text-muted">{hint}</span>}
      {error && <span className="text-[11px] text-failure">{error}</span>}
    </label>
  )
}

function ScenarioCard({ scenario, onOpen }: { scenario: Scenario; onOpen: () => void }) {
  return (
    <Card
      className="cursor-pointer transition-colors hover:border-electric/40"
          >
      <div onClick={onOpen} className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-xs text-text-muted">{scenario.id}</span>
          <Badge tone={DIFFICULTY_TONES[scenario.difficulty]}>
            {scenario.difficulty}
          </Badge>
        </div>
        <div className="text-sm font-semibold text-text-primary">
          {scenario.type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
        </div>
        <p className="line-clamp-2 text-xs text-text-muted">“{scenario.caller}”</p>
        <div className="flex flex-wrap gap-1.5">
          <Badge tone="neutral">{scenario.language}</Badge>
          {scenario.track && <Badge tone="cyan">{scenario.track}</Badge>}
        </div>
        <div>
          <span className="text-[11px] font-medium uppercase tracking-wider text-text-muted">
            Caller intent
          </span>
          <p className="mt-0.5 text-xs text-text-primary">{scenario.expected}</p>
        </div>
      </div>
    </Card>
  )
}

function ScenarioDetailDrawer({
  scenario,
  onClose,
}: {
  scenario: Scenario | null
  onClose: () => void
}) {
  return (
    <AnimatePresence>
      {scenario && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-void/75"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.98 }}
            transition={{ duration: 0.2 }}
          >
            <div className="shadow-custom max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-lg border border-line bg-panel p-6">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <div className="font-mono text-xs text-text-muted">{scenario.id}</div>
                  <h3 className="text-base font-semibold text-text-primary">
                    {scenario.type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </h3>
                </div>
                <button
                  onClick={onClose}
                  className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-panel-raised hover:text-text-primary"
                  aria-label="Close details"
                >
                  ✕
                </button>
              </div>
              <div className="flex flex-col gap-4">
                <DetailRow label="Difficulty">
                  <Badge tone={DIFFICULTY_TONES[scenario.difficulty]}>{scenario.difficulty}</Badge>
                </DetailRow>
                <DetailRow label="Language">
                  <Badge tone="neutral">{scenario.language}</Badge>
                </DetailRow>
                {scenario.track && (
                  <DetailRow label="Track">
                    <Badge tone="cyan">{scenario.track}</Badge>
                  </DetailRow>
                )}
                <DetailRow label="Conditions">
                  <div className="flex flex-wrap gap-1.5">
                    {scenario.conditions.length ? (
                      scenario.conditions.map((c) => (
                        <Badge key={c} tone="cyan">
                          {c}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-xs text-text-muted">None</span>
                    )}
                  </div>
                </DetailRow>
                <DetailRow label="Caller intent / input">
                  <p className="text-sm text-text-primary">“{scenario.caller}”</p>
                </DetailRow>
                <DetailRow label="Expected agent behavior">
                  <p className="text-sm text-text-primary">{scenario.expected}</p>
                </DetailRow>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-widest text-text-muted">
        {label}
      </div>
      {children}
    </div>
  )
}
