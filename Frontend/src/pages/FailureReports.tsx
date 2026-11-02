import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  evaluationRecords,
  failureReportsFromRecords,
  type FailureReport,
  type ReportSeverity,
} from '../api/failureReportsApi'
import type { BenchmarkSummary } from '../api/client'
import { apiGet } from '../api/client'
import { PageSection, PageShell } from '../components/layout/PageShell'
import { EmptyState, ErrorState, LoadingState } from '../components/states'
import { Badge, Card, CardTitle } from '../components/ui'

const SEVERITY_TONES: Record<ReportSeverity, 'red' | 'warn' | 'cyan' | 'neutral'> = {
  critical: 'red',
  major: 'warn',
  minor: 'cyan',
  unweighted: 'neutral',
}

const SEVERITY_LABELS: Record<ReportSeverity, string> = {
  critical: 'Critical (crash weight 40 / safety)',
  major: 'Major (crash weight 30)',
  minor: 'Minor (crash weight 20)',
  unweighted: 'Unweighted',
}

export default function FailureReports() {
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [reports, setReports] = useState<FailureReport[]>([])
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [severityFilter, setSeverityFilter] = useState<'all' | ReportSeverity>('all')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [benchmarks, setBenchmarks] = useState<BenchmarkSummary[]>([])
  const [benchmarkId, setBenchmarkId] = useState<string>('')

  useEffect(() => {
    let active = true
    apiGet<{ items: BenchmarkSummary[] }>('/api/benchmarks')
      .then((r) => {
        if (!active) return
        setBenchmarks(r.items)
        setBenchmarkId((cur) => cur || r.items[0]?.benchmark_id || '')
        setState('ready')
      })
      .catch((e: Error) => {
        if (!active) return
        setError(e.message)
        setState('error')
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    let active = true
    if (!benchmarkId) return
    setState('loading')
    evaluationRecords(benchmarkId)
      .then((bundle) => {
        if (!active) return
        setReports(failureReportsFromRecords(bundle.evaluation_records ?? []))
        setState('ready')
        setError(null)
      })
      .catch((e: Error) => {
        if (!active) return
        setReports([])
        setError(e.message)
        setState('error')
      })
    return () => {
      active = false
    }
  }, [benchmarkId])

  const categories = useMemo(
    () => [...new Set(reports.map((r) => r.category))],
    [reports],
  )

  const filtered = useMemo(
    () =>
      reports
        .filter((r) => categoryFilter === 'all' || r.category === categoryFilter)
        .filter((r) => severityFilter === 'all' || r.severity === severityFilter)
        .sort((a, b) => {
          const rank = { critical: 0, major: 1, minor: 2, unweighted: 3 } as const
          return rank[a.severity] - rank[b.severity]
        }),
    [reports, categoryFilter, severityFilter],
  )

  const severityCounts = useMemo(() => {
    const counts: Partial<Record<ReportSeverity, number>> = {}
    for (const r of reports) counts[r.severity] = (counts[r.severity] ?? 0) + 1
    return counts
  }, [reports])

  if (state === 'error') {
    return (
      <PageShell>
        <ErrorState title="Failed to load reports" message={error ?? ''} onRetry={() => setState('loading')} />
      </PageShell>
    )
  }

  return (
    <PageShell>
      <div className="flex flex-col gap-6">
        {benchmarks.length > 0 && (
          <Card className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Evaluation records</CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                Persisted evaluation_results.json from the backend run for the selected benchmark.
              </p>
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
        )}

        {state === 'loading' ? (
          <LoadingState label="Loading failure reports…" />
        ) : (
          <>
            <PageSection title="Filters">
              <Card className="flex flex-col gap-3 ">
                <FilterRow label="Category">
                  <FilterButton active={categoryFilter === 'all'} onClick={() => setCategoryFilter('all')}>
                    all
                  </FilterButton>
                  {categories.map((c) => (
                    <FilterButton key={c} active={categoryFilter === c} onClick={() => setCategoryFilter(c)}>
                      {c}
                    </FilterButton>
                  ))}
                </FilterRow>
                <FilterRow label="Severity">
                  <FilterButton active={severityFilter === 'all'} onClick={() => setSeverityFilter('all')}>
                    all
                  </FilterButton>
                  {(['critical', 'major', 'minor', 'unweighted'] as ReportSeverity[]).map((s) => (
                    <FilterButton key={s} active={severityFilter === s} onClick={() => setSeverityFilter(s)}>
                      {s} {severityCounts[s] ? `(${severityCounts[s]})` : ''}
                    </FilterButton>
                  ))}
                </FilterRow>
                <p className="text-[10px] text-text-muted">
                  Severity is derived from <span className="font-mono">evaluator/crash_score.py</span>{' '}
                  category weights: STT=40 → critical, 30 → major, 20 → minor. SAFETY_FAILURE is
                  treated as critical by the judge but carries no crash-score weight.
                </p>
              </Card>
            </PageSection>

            <PageSection title={`Failure reports (${filtered.length})`}>
              {filtered.length === 0 ? (
                <EmptyState
                  icon="✅"
                  title="No failures match the filters"
                  description={
                    reports.length === 0
                      ? 'All evaluated tests passed for this benchmark, or no run has been evaluated yet.'
                      : 'Adjust the category or severity filters.'
                  }
                  action={
                    reports.length > 0 ? (
                      <FilterButton active={false} onClick={() => { setCategoryFilter('all'); setSeverityFilter('all') }}>
                        Reset filters
                      </FilterButton>
                    ) : undefined
                  }
                />
              ) : (
                <div className="flex flex-col gap-3">
                  {filtered.map((r) => (
                    <ReportCard
                      key={r.test_id}
                      report={r}
                      expanded={expanded === r.test_id}
                      onToggle={() => setExpanded((e) => (e === r.test_id ? null : r.test_id))}
                    />
                  ))}
                </div>
              )}
            </PageSection>
          </>
        )}
      </div>
    </PageShell>
  )
}

function ReportCard({
  report,
  expanded,
  onToggle,
}: {
  report: FailureReport
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <Card className=" overflow-hidden">
      <button
        onClick={onToggle}
        className="flex w-full flex-wrap items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-panel-raised/60"
      >
        <Badge tone={SEVERITY_TONES[report.severity]}>{report.severity.toUpperCase()}</Badge>
        <Badge tone="neutral">{report.category}</Badge>
        <span className="font-mono text-xs text-text-muted">{report.test_id}</span>
        <span className="min-w-0 flex-1 truncate text-xs text-text-muted">
          {report.scenario_type.replace(/_/g, ' ')}
        </span>
      </button>
      {expanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="flex flex-col gap-3 border-t border-line px-4 py-4 text-xs"
        >
          <Row label="Scenario">
            {report.scenario_id} · {report.scenario_type.replace(/_/g, ' ')}
            {report.attack_type ? ` · attack: ${report.attack_type.replace(/_/g, ' ')}` : ''}
          </Row>
          <Row label="Severity">
            {SEVERITY_LABELS[report.severity]}
          </Row>
          <Row label="Expected behavior">{report.expected}</Row>
          <Row label="Actual behavior (agent response)">“{report.agent_response}”</Row>
          <Row label="Explanation / evidence">{report.reason || 'No evaluation reason recorded.'}</Row>
          <Row label="Suggested next action (LLM suggestion, not a confirmed fix)">
            {report.suggestedFix ?? 'No suggestion recorded for this failure.'}
          </Row>
        </motion.div>
      )}
    </Card>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-text-muted">
        {label}
      </div>
      <div className="text-text-primary">{children}</div>
    </div>
  )
}

function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="w-16 text-[11px] font-medium uppercase tracking-wider text-text-muted">
        {label}
      </span>
      {children}
    </div>
  )
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors ${
        active
          ? 'border-line bg-signal/10 text-text-primary'
          : 'border-line bg-panel-raised text-text-muted hover:text-text-primary'
      }`}
    >
      {children}
    </button>
  )
}


