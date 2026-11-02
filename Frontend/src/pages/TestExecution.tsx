import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  DEFAULT_AGENT_CONFIG,
  connectAgent,
  executionStatus,
  runResults,
  startRun,
  type AgentConfig,
  type ExecutableTest,
  type RunResults,
} from '../api/executionApi'
import type { BenchmarkSummary, ManifestItem } from '../api/client'
import { apiGet } from '../api/client'
import { PageSection, PageShell } from '../components/layout/PageShell'
import { EmptyState, ErrorState, LoadingState } from '../components/states'
import { Badge, Button, Card, CardTitle, StatusIndicator } from '../components/ui'
import { motion } from 'framer-motion'

/** ExecutableTest enriched with the details required for result rows. */

export default function TestExecution() {
  const [benchmarks, setBenchmarks] = useState<BenchmarkSummary[]>([])
  const [benchmarkId, setBenchmarkId] = useState<string>('')
  const [config, setConfig] = useState<AgentConfig>(DEFAULT_AGENT_CONFIG)
  const [connection, setConnection] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [tests, setTests] = useState<ExecutableTest[]>([])
  const [runState, setRunState] = useState<'idle' | 'running' | 'finished'>('idle')
  const [runError, setRunError] = useState<string | null>(null)
  const [loading, setLoading] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)
  const [progress, setProgress] = useState({ completed: 0, total: 0 })

  const loadBenchmarks = useCallback(() => {
    let active = true
    setLoading('loading')
    apiGet<{ items: BenchmarkSummary[] }>('/api/benchmarks')
      .then((r) => {
        if (!active) return
        setBenchmarks(r.items)
        setBenchmarkId((current) => current || r.items[0]?.benchmark_id || '')
        setLoading('ready')
        setError(null)
      })
      .catch((e: Error) => {
        if (!active) return
        setError(e.message)
        setLoading('error')
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => loadBenchmarks(), [loadBenchmarks])

  /* Load manifest whenever a benchmark is selected. */
  useEffect(() => {
    let active = true
    if (!benchmarkId) return
    apiGet<{ items: ManifestItem[] }>(`/api/manifest/${encodeURIComponent(benchmarkId)}`)
      .then((manifest) => {
        if (!active) return
        setTests(
          (manifest.items ?? []).map((item) => ({
            test_id: item.test_id,
            scenario_id: item.scenario_id,
            category: item.category,
            scenario_type: item.scenario_type,
            condition: item.condition,
            attack_type: item.attack_type,
            attack_level: item.attack_level,
            expected: item.expected,
            caller_input: null,
            status: 'pending' as const,
          })),
        )
        setRunState('idle')
        setRunError(null)
      })
      .catch((e: Error) => {
        if (!active) return
        setTests([])
        setRunError(e.message)
        setRunState('idle')
      })
    return () => {
      active = false
    }
  }, [benchmarkId])

  /* Restore any results already persisted for this benchmark. */
  useEffect(() => {
    let active = true
    if (runState !== 'idle') return
    if (!benchmarkId) return
    runResults(benchmarkId)
      .then((results) => {
        if (!active) return
        setTests((prev) => mergeResults(prev, results))
      })
      .catch(() => undefined) // no run yet for this benchmark — fine
    return () => {
      active = false
    }
  }, [benchmarkId, runState])

  const poll = useCallback(async (id: string) => {
    try {
      const status = await executionStatus(id)
      // Results are withheld until the run finishes — only progress is shown live.
      setProgress({ completed: status.completed, total: status.total })
      if (status.running) {
        pollRef.current = window.setTimeout(() => poll(id), 2000)
      } else {
        setRunState('finished')
        const results = await runResults(id)
        setTests((prev) => mergeResults(prev, results))
      }
    } catch {
      setRunError('Lost connection to the backend while polling run status.')
      setRunState('idle')
    }
  }, [])

  useEffect(() => () => {
    if (pollRef.current) window.clearTimeout(pollRef.current)
  }, [])

  const handleConnect = async () => {
    if (connecting) return
    setConnecting(true)
    setConnection(null)
    try {
      const res = await connectAgent(config)
      setConnection(res.message || 'Endpoint reachable.')
    } catch (e) {
      setConnection(e instanceof Error ? e.message : String(e))
    } finally {
      setConnecting(false)
    }
  }

  const handleStart = async () => {
    if (runState === 'running') return
    setRunError(null)
    try {
      const res = await startRun(benchmarkId, config)
      setRunState('running')
      setProgress({ completed: 0, total: tests.length })
      setTests((prev) => prev.map((t) => ({ ...t, status: 'pending' as const, evaluation: undefined, agent_response: undefined, suggested_fix: undefined })))
      void poll(benchmarkId)
      void res
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e))
    }
  }

  const stats = useMemo(() => {
    const total = tests.length
    const done = tests.filter((t) => !['pending', 'running'].includes(t.status)).length
    const passed = tests.filter((t) => t.evaluation?.passed === true).length
    return { total, done, passed, failed: done - passed }
  }, [tests])

  // While a run is in flight, numbers come from the backend status endpoint
  // (per-test results are only merged in when the run completes).
  const liveDone = runState === 'running' ? progress.completed : stats.done
  const liveTotal = runState === 'running' ? progress.total || stats.total : stats.total

  const benchmarkLabel = useMemo(
    () => benchmarks.find((b) => b.benchmark_id === benchmarkId)?.agent_role ?? benchmarkId,
    [benchmarks, benchmarkId],
  )

  if (loading === 'loading') {
    return (
      <PageShell>
        <LoadingState label="Loading benchmarks…" />
      </PageShell>
    )
  }
  if (loading === 'error') {
    return (
      <PageShell>
        <ErrorState
          title="Backend unreachable"
          message={error ?? ''}
          onRetry={loadBenchmarks}
        />
      </PageShell>
    )
  }

  return (
    <PageShell>
      <div className="flex flex-col gap-6">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <CardTitle>Agent connection</CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                Configure the HTTP audio-in agent. Field names mirror the backend
                adapter defaults.
              </p>
            </div>
            <div className="flex items-center gap-3">
              {connection && (
                <StatusIndicator
                  status={connection.toLowerCase().includes('reachable') ? 'online' : 'offline'}
                  label={connection}
                />
              )}
              <Button size="sm" variant="secondary" onClick={handleConnect} disabled={connecting}>
                {connecting ? 'Testing…' : 'Test connection'}
              </Button>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Agent endpoint URL">
              <input
                className="input-base"
                placeholder="https://your-agent/api/voice"
                value={config.endpoint}
                onChange={(e) => setConfig({ ...config, endpoint: e.target.value })}
              />
            </Field>
            <Field label="Agent name">
              <input
                className="input-base"
                value={config.name}
                onChange={(e) => setConfig({ ...config, name: e.target.value })}
              />
            </Field>
            <Field label="Token (optional, stored only during this session)">
              <input
                className="input-base"
                type="password"
                value={config.token}
                onChange={(e) => setConfig({ ...config, token: e.target.value })}
              />
            </Field>
            <Field label="Multipart audio field">
              <input
                className="input-base"
                value={config.input_field}
                onChange={(e) => setConfig({ ...config, input_field: e.target.value })}
              />
            </Field>
            <Field label="Text response field (dotted JSON path ok)">
              <input
                className="input-base"
                value={config.response_text_field}
                onChange={(e) => setConfig({ ...config, response_text_field: e.target.value })}
              />
            </Field>
            <Field label="Response audio URL field">
              <input
                className="input-base"
                value={config.response_audio_url_field}
                onChange={(e) => setConfig({ ...config, response_audio_url_field: e.target.value })}
              />
            </Field>
          </div>
        </Card>

        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <CardTitle>Run: {benchmarkLabel || 'No benchmark selected'}</CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                {runState === 'running'
                  ? `${liveDone}/${liveTotal} tests processed, results shown when the run completes`
                  : `${stats.total} tests · ${stats.done} processed · ${stats.passed} passed · ${stats.failed} failed/review`}
              </p>
            </div>
            <div className="flex gap-2">
              {runState === 'running' ? (
                <StatusIndicator status="warning" label="Run in progress…" />
              ) : (
                <Button size="sm" onClick={handleStart} disabled={!benchmarkId || !config.endpoint}>
                  {stats.done > 0 && stats.done < stats.total ? 'Resume / re-run suite' : 'Start test run'}
                </Button>
              )}
            </div>
          </div>

          {benchmarkId && (
            <div className="mt-3">
              <label className="text-[11px] font-medium text-text-muted">Test suite</label>
              <select
                className="input-base mt-1"
                value={benchmarkId}
                onChange={(e) => setBenchmarkId(e.target.value)}
              >
                {benchmarks.map((b) => (
                  <option key={b.benchmark_id} value={b.benchmark_id}>
                    {b.agent_role} · {b.scenario_count} scenarios · {b.language}
                  </option>
                ))}
              </select>
            </div>
          )}

          {tests.length > 0 && (
            <div className="mt-4">
              <div className="mb-1 flex justify-between text-[11px] text-text-muted">
                <span>
                  {liveDone}/{liveTotal} processed
                </span>
                <span>{Math.round((liveDone / Math.max(liveTotal, 1)) * 100)}%</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel-raised">
                <motion.div
                  className="dashboard-progress-fill h-full rounded-full bg-gradient-to-r from-signal to-electric"
                  key={liveDone}
                  initial={{ width: 0 }}
                  animate={{ width: `${(liveDone / Math.max(liveTotal, 1)) * 100}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
            </div>
          )}
          {runError && (
            <p className="mt-3 text-xs text-failure">{runError}</p>
          )}
        </Card>

        <PageSection title="Test results">
          {tests.length === 0 ? (
            <EmptyState
              icon="🧪"
              title="No manifest loaded"
              description="Generate a suite in Scenario Lab first; the manifest from data/manifests will appear here."
            />
          ) : (
            <div className="flex flex-col gap-2.5">
              {tests.map((t) => (
                <TestRow
                  key={t.test_id}
                  test={t}
                  expanded={expanded === t.test_id}
                  onToggle={() => setExpanded((e) => (e === t.test_id ? null : t.test_id))}
                />
              ))}
            </div>
          )}
        </PageSection>
      </div>
    </PageShell>
  )
}

function mergeResults(prev: ExecutableTest[], results: RunResults): ExecutableTest[] {
  const responseByTest = new Map<string, RunResults['agent_responses'][number]>()
  for (const r of results.agent_responses ?? []) responseByTest.set(r.test_id, r)
  const recordByTest = new Map<string, RunResults['evaluation_records'][number]>()
  for (const r of results.evaluation_records ?? []) recordByTest.set(r.test_id, r)
  return prev.map((t) => {
    const record = recordByTest.get(t.test_id)
    const response = responseByTest.get(t.test_id)
    if (!record && !response) return t
    return {
      ...t,
      status: (record?.status ?? response?.status) as ExecutableTest['status'],
      agent_response:
        record?.agent_response ??
        response?.agent_response ??
        response?.response_text ??
        undefined,
      evaluation: record?.evaluation as ExecutableTest['evaluation'],
      suggested_fix: record?.suggested_fix,
      response_audio_path: response?.response_audio_path,
      caller_input: record?.caller_transcript ?? t.caller_input,
    }
  })
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-text-primary">{label}</span>
      {children}
    </label>
  )
}

function TestRow({
  test,
  expanded,
  onToggle,
}: {
  test: ExecutableTest
  expanded: boolean
  onToggle: () => void
}) {
  const passed = test.evaluation?.passed === true
  const hasResult = !['pending', 'running'].includes(test.status)
  return (
    <Card className="overflow-hidden">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-panel-raised/60"
      >
        <ResultBadge test={test} />
        <span className="font-mono text-xs text-text-muted">{test.test_id}</span>
        <span className="hidden min-w-0 flex-1 truncate text-xs text-text-muted sm:inline">
          {test.scenario_type.replace(/_/g, ' ')}
          {test.attack_type ? ` · ${test.attack_type.replace(/_/g, ' ')}` : ''}
        </span>
        {expanded && <span className="text-[10px] text-text-muted">▲</span>}
      </button>
      {expanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="flex flex-col gap-3 border-t border-line px-4 py-4 text-xs"
        >
          <DetailRow label="Caller input">{test.caller_input ?? '-'}</DetailRow>
          <DetailRow label="Agent response">
            {hasResult ? test.agent_response || 'No response received.' : test.status === 'running' ? 'Waiting for response…' : '-'}
          </DetailRow>
          <DetailRow label="Expected behavior">{test.expected}</DetailRow>
          {hasResult && (
            <DetailRow label="Result">
              {passed ? (
                <Badge tone="green">PASS</Badge>
              ) : (
                <Badge tone="red">FAIL · {test.evaluation?.category ?? 'FAILED'}</Badge>
              )}
            </DetailRow>
          )}
          {!passed && hasResult && test.evaluation?.reason && (
            <DetailRow label="Failure details">{test.evaluation.reason}</DetailRow>
          )}
          {!passed && hasResult && test.suggested_fix && (
            <DetailRow label="Suggested fix">{test.suggested_fix}</DetailRow>
          )}
          <DetailRow label="Metadata">
            <div className="flex flex-wrap gap-1.5">
              <Badge tone="neutral">{test.condition}</Badge>
              {test.attack_type && <Badge tone="warn">{test.attack_type.replace(/_/g, ' ')}</Badge>}
              {test.attack_level && <Badge tone="neutral">{test.attack_level}</Badge>}
            </div>
          </DetailRow>
        </motion.div>
      )}
    </Card>
  )
}

function ResultBadge({ test }: { test: ExecutableTest }) {
  if (test.status === 'pending') return <Badge tone="neutral">PENDING</Badge>
  if (test.status === 'running')
    return (
      <Badge tone="highlight">
        <motion.span animate={{ opacity: [1, 0.4, 1] }} transition={{ duration: 1.2, repeat: Infinity }}>
          RUNNING
        </motion.span>
      </Badge>
    )
  if (test.status === 'responded')
    return (
      <Badge tone="cyan">
        <motion.span animate={{ opacity: [1, 0.4, 1] }} transition={{ duration: 1.2, repeat: Infinity }}>
          EVALUATING
        </motion.span>
      </Badge>
    )
  if (test.status === 'failed' || test.status === 'evaluation_failed')
    return <Badge tone="red">{test.status === 'failed' ? 'NO RESPONSE' : 'EVAL FAILED'}</Badge>
  return test.evaluation?.passed === true ? (
    <Badge tone="green">🟢 PASS</Badge>
  ) : (
    <Badge tone="red">🔴 {shortCategory(test.evaluation?.category)}</Badge>
  )
}

function shortCategory(cat?: string) {
  if (!cat) return 'FAIL'
  return cat.replace(/_FAILURE$/, '').replace(/_/g, ' ')
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-text-muted">
        {label}
      </div>
      <div className="text-text-primary">{children}</div>
    </div>
  )
}
