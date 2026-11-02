import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts'
import { PageSection, PageShell } from '../components/layout/PageShell'
import { ErrorState, EmptyState, LoadingState } from '../components/states'
import { Badge, Card, StatusIndicator } from '../components/ui'
import { fetchHealth, apiGet, type BackendHealth, type BenchmarkSummary } from '../api/client'
import { evaluationRecords } from '../api/failureReportsApi'
import { CRASH_SCORE_WEIGHTS } from '../api/failureReportsApi'
import { aggregate, type EvaluationRecord, type RunSummary } from '../types/evaluation'

export default function Overview() {
  const [attempt, setAttempt] = useState(0)
  const [health, setHealth] = useState<BackendHealth | null>(null)
  const [benchmarks, setBenchmarks] = useState<BenchmarkSummary[]>([])
  const [benchmarkId, setBenchmarkId] = useState<string>('')
  const [records, setRecords] = useState<EvaluationRecord[] | null>(null)
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    fetchHealth()
      .then((h) => active && setHealth(h))
      .catch(() => {
        /* offline — shown via StatusIndicator */
      })
    apiGet<{ items: BenchmarkSummary[] }>('/api/benchmarks')
      .then((r) => {
        if (!active) return
        setBenchmarks(r.items)
        setBenchmarkId((cur) => cur || r.items[0]?.benchmark_id || '')
      })
      .catch((e: Error) => active && setError(e.message))
    return () => {
      active = false
    }
  }, [attempt])

  useEffect(() => {
    let active = true
    if (!benchmarkId) {
      setRecords([])
      setRuns([])
      return
    }
    setRecords(null)
    evaluationRecords(benchmarkId)
      .then((bundle) => {
        if (!active) return
        setRecords(bundle.evaluation_records ?? [])
        setRuns(
          benchmarks.map((b) => ({
            id: b.benchmark_id,
            label: `${b.agent_role} · ${b.scenario_count} scenarios`,
            created_at: b.updated_at,
            totalTests: b.scenario_count,
            passed: 0,
            failed: 0,
            criticalFailures: 0,
          })),
        )
      })
      .catch((e: Error) => {
        if (!active) return
        setRecords([])
        setError(e.message)
      })
    return () => {
      active = false
    }
  }, [benchmarkId, benchmarks])

  const totals = useMemo(() => aggregate(records ?? []), [records])
  const noData = totals.total === 0

  const avgCrashWeight = useMemo(() => {
    const failed = (records ?? []).filter(
      (r) => r.evaluation?.passed !== true && r.evaluation?.category,
    )
    if (failed.length === 0) return null
    const sum = failed.reduce((acc, r) => acc + (CRASH_SCORE_WEIGHTS[r.evaluation.category!] ?? 0), 0)
    return sum / failed.length
  }, [records])

  const distribution = useMemo(() => {
    const counts = new Map<string, number>()
    for (const r of records ?? []) {
      if (r.evaluation?.passed === true) continue
      const key = r.evaluation?.category ?? 'FAILED'
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([category, count]) => ({ category, count }))
  }, [records])

  const activity = useMemo(
    () =>
      [...(records ?? [])]
        .sort((a, b) => (b.evaluated_at ?? '').localeCompare(a.evaluated_at ?? ''))
        .slice(0, 5),
    [records],
  )

  if (error) {
    return (
      <PageShell>
        <ErrorState title="Failed to load run data" message={error} onRetry={() => setAttempt((a) => a + 1)} />
      </PageShell>
    )
  }

  return (
    <PageShell>
      <div className="flex flex-col gap-6">
        <Card className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <StatusIndicator
              status={health ? 'online' : 'offline'}
              label={health ? `Backend connected${health.features.llm_fix_suggestions ? ' · LLM suggestions on' : ''}` : 'Backend not reachable'}
            />
          </div>
          <select
            value={benchmarkId}
            onChange={(e) => setBenchmarkId(e.target.value)}
            className="input-base w-full max-w-sm"
          >
            {benchmarks.map((b) => (
              <option key={b.benchmark_id} value={b.benchmark_id}>
                {b.agent_role} · {b.scenario_count} scenarios · {b.language}
              </option>
            ))}
          </select>
        </Card>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          <MetricCard label="Total tests executed" value={noData ? '-' : totals.total} />
          <MetricCard label="Pass rate" value={noData ? '-' : `${totals.passRate.toFixed(1)}%`} tone="cyan" />
          <MetricCard label="Failed tests" value={noData ? '-' : totals.failed} tone={totals.failed ? 'red' : 'neutral'} />
          <MetricCard label="Critical failures" value={noData ? '-' : totals.critical} tone={totals.critical ? 'red' : 'neutral'} />
          <MetricCard
            label="Avg crash weight / failure"
            value={noData || avgCrashWeight === null ? '-' : avgCrashWeight.toFixed(0)}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <PageSection title="Failure distribution">
            {records === null ? (
              <LoadingState label="Loading results…" />
            ) : distribution.length === 0 ? (
              <EmptyState icon="🧾" title="No failures recorded" description="Failure counts by category will be charted here." />
            ) : (
              <Card>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={distribution} margin={{ top: 8, right: 8, bottom: 40, left: 0 }}>
                      <CartesianGrid stroke="var(--color-line)" strokeDasharray="3 3" vertical={false} />
                      <XAxis
                        dataKey="category"
                        tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
                        angle={-35}
                        textAnchor="end"
                        interval={0}
                      />
                      <YAxis allowDecimals={false} tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }} width={28} />
                      <RechartsTooltip
                        contentStyle={{ background: 'var(--color-panel-raised)', border: '1px solid var(--color-line)', borderRadius: 8, fontSize: 12, color: 'var(--color-text-primary)' }}
                        cursor={{ fill: 'color-mix(in oklab, var(--color-signal) 8%, transparent)' }}
                      />
                      <Bar dataKey="count" fill="var(--color-signal)" radius={[6, 6, 0, 0]} maxBarSize={42} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            )}
          </PageSection>

          <PageSection title="Benchmarks">
            {runs === null ? (
              <LoadingState label="Loading benchmarks…" />
            ) : runs.length === 0 ? (
              <EmptyState icon="🗂️" title="No benchmarks yet" description="Generate a suite in Scenario Lab to create one." />
            ) : (
              <div className="flex flex-col gap-3">
                {runs.map((run) => (
                  <Card
                    key={run.id}
                    className={`flex cursor-pointer items-center justify-between gap-4 transition-colors hover:border-signal/40 ${
                      run.id === benchmarkId ? 'border-signal/50' : ''
                    }`}
                  >
                    <button className="min-w-0 flex-1 text-left" onClick={() => setBenchmarkId(run.id)}>
                      <div className="truncate text-sm font-medium text-text-primary">{run.label}</div>
                      <div className="text-xs text-text-muted">{new Date(run.created_at).toLocaleString()}</div>
                    </button>
                    <Badge tone={run.id === benchmarkId ? 'cyan' : 'neutral'}>
                      {run.id === benchmarkId ? 'viewing' : 'select'}
                    </Badge>
                  </Card>
                ))}
              </div>
            )}
          </PageSection>
        </div>

        <PageSection title="Recent activity">
          {records === null ? (
            <LoadingState label="Loading activity…" />
          ) : activity.length === 0 ? (
            <EmptyState
              icon="📡"
              title="No evaluation activity yet"
              description="Run a benchmark execution to see evaluated results here."
              action={
                <button
                  onClick={() => navigate('/test-execution')}
                  className="inline-flex h-8 items-center rounded-lg border border-signal/40 bg-signal/20 px-3 text-xs font-medium text-signal-hover transition-colors hover:bg-signal/15"
                >
                  Go to Test Execution
                </button>
              }
            />
          ) : (
            <div className="flex flex-col gap-2.5">
              {activity.map((r) => {
                const passed = r.evaluation.passed === true
                const tag = passed ? 'PASS' : r.evaluation.category ?? 'FAILED'
                return (
                  <div
                    key={r.test_id}
                    className="flex items-center gap-3 rounded-lg border border-line bg-panel px-4 py-2.5"
                  >
                    <Badge tone={passed ? 'green' : 'red'}>{passed ? '🟢' : '🔴'} {tag}</Badge>
                    <span className="font-mono text-xs text-text-muted">{r.test_id}</span>
                    <span className="min-w-0 flex-1 truncate text-xs text-text-muted">
                      {passed ? r.scenario_id : r.evaluation.reason ?? '-'}
                    </span>
                    <span className="hidden shrink-0 text-[11px] text-text-muted sm:inline">
                      {new Date(r.evaluated_at).toLocaleTimeString()}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </PageSection>
      </div>
    </PageShell>
  )
}

function MetricCard({
  label,
  value,
  tone = 'neutral',
}: {
  label: string
  value: string | number
  tone?: 'neutral' | 'red' | 'cyan'
}) {
  const valueColor =
    tone === 'red' ? 'text-failure' : tone === 'cyan' ? 'text-electric' : 'text-text-primary'
  const border =
    tone === 'red' && value !== 0 && value !== '0.0%'
      ? 'border border-failure/40'
      : 'border border-line'
  return (
    <Card className={`${border} flex flex-col gap-1.5`}>
      <h2 className="truncate text-sm font-medium text-text-muted">{label}</h2>
      <span className={`text-3xl font-semibold leading-none ${valueColor}`}>{value}</span>
    </Card>
  )
}
