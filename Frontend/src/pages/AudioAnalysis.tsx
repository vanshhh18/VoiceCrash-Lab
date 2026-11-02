import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchAudioSuite, hasPlayableAudio, type AudioEntry, type AudioSuite } from '../api/audioApi'
import type { BenchmarkSummary } from '../api/client'
import { apiGet } from '../api/client'
import { PageSection, PageShell } from '../components/layout/PageShell'
import { EmptyState, ErrorState, LoadingState } from '../components/states'
import { Badge, Card, CardTitle } from '../components/ui'

const ATTACK_DESCRIPTIONS: Record<string, string> = {
  traffic_noise: 'Traffic scene noise mixed at negative SNR.',
  fan_noise: 'Fan noise mixed at -10 dB SNR.',
  phone_line: 'Telephone band-limiting and compression artifacts.',
  audio_dropouts: 'Repeated short silent gaps in the audio.',
  muffled_speech: 'Speech low-pass filtered around 2 kHz.',
  cutoff: 'Utterance truncated partway through.',
  interruption: 'Overlaid speech interrupting mid-utterance.',
}

export default function AudioAnalysis() {
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [benchmarks, setBenchmarks] = useState<BenchmarkSummary[]>([])
  const [benchmarkId, setBenchmarkId] = useState<string>('')
  const [suite, setSuite] = useState<AudioSuite | null>(null)
  const [playingId, setPlayingId] = useState<string | null>(null)
  const [selected, setSelected] = useState<AudioEntry | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

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
    fetchAudioSuite(benchmarkId)
      .then((s) => {
        if (!active) return
        setSuite(s)
        setError(null)
      })
      .catch((e: Error) => {
        if (!active) return
        setError(e.message)
        setState('error')
      })
    return () => {
      active = false
    }
  }, [benchmarkId])

  const transcripts = useMemo(() => {
    const map = new Map<string, string>()
    for (const entry of suite?.entries ?? []) {
      if (!map.has(entry.scenario_id)) {
        map.set(entry.scenario_id, entry.scenario_type)
      }
    }
    return map
  }, [suite])

  const activeEntry = playingId

  const handlePlay = (entry: AudioEntry) => {
    if (!hasPlayableAudio(entry)) return
    if (activeEntry === entry.test_id) {
      audioRef.current?.pause()
      setPlayingId(null)
      return
    }
    const el = audioRef.current
    if (el) {
      el.src = entry.src
      el.play()
        .then(() => setPlayingId(entry.test_id))
        .catch(() => setPlayingId(entry.test_id))
    }
  }

  if (state === 'error') {
    return (
      <PageShell>
        <ErrorState
          title="Failed to load recordings"
          message={error ?? ''}
          onRetry={() => setState('loading')}
        />
      </PageShell>
    )
  }

  return (
    <PageShell>
      <audio
        ref={audioRef}
        onEnded={() => setPlayingId(null)}
        onError={() => setPlayingId(null)}
        className="hidden"
      />

      <div className="flex flex-col gap-6">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Recording suite</CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                Audio served by the backend from data/recordings and data/attacked.
              </p>
            </div>
            <div>
              <label className="text-[11px] font-medium text-text-muted">Benchmark</label>
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
          </div>
        </Card>

        {state === 'loading' ? (
          <LoadingState label="Loading recordings…" />
        ) : suite && suite.entries.length > 0 ? (
          <PageSection title={`Recordings · ${suite.label}`}>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {suite.entries.map((entry) => {
                const playable = hasPlayableAudio(entry)
                const isPlaying = playingId === entry.test_id
                return (
                  <Card key={entry.test_id}>
                    <div className="flex flex-col gap-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="font-mono text-[11px] text-text-muted">
                            {entry.test_id} · {entry.scenario_type.replace(/_/g, ' ')}
                          </div>
                          <CardTitle className="mt-0.5 block">
                            {entry.condition === 'clean' ? 'Clean recording' : 'Attacked recording'}
                          </CardTitle>
                        </div>
                        <Badge tone={entry.condition === 'clean' ? 'green' : 'warn'}>
                          {entry.condition === 'clean' ? 'clean' : entry.attack_type?.replace(/_/g, ' ')}
                        </Badge>
                      </div>

                      {entry.attack_type && (
                        <div className="rounded-lg border border-line bg-panel-raised/60 px-3 py-2 text-[11px] text-text-muted">
                          <span className="font-semibold text-signal-hover">Attack: </span>
                          {entry.attack_type.replace(/_/g, ' ')}
                          {entry.attack_level ? ` · ${entry.attack_level}` : ''}{' '}
                          {ATTACK_DESCRIPTIONS[entry.attack_type] ?? 'Audio attenuation attack.'}
                        </div>
                      )}

                      <div className="text-[11px] text-text-muted">
                        Scenario: {entry.scenario_id} · {entry.language}
                      </div>

                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handlePlay(entry)}
                          disabled={!playable}
                          aria-label={`Play ${entry.test_id}`}
                          className={`flex h-9 w-9 items-center justify-center rounded-full border transition-colors ${
                            playable
                              ? 'border-signal/50 bg-signal text-void hover:bg-signal-hover'
                              : 'cursor-not-allowed border-line bg-panel-raised text-text-muted opacity-60'
                          }`}
                        >
                          {isPlaying ? '⏸' : '▶'}
                        </button>
                        {!playable && (
                          <span className="text-[11px] text-text-muted">
                            File missing from the backend data directory
                          </span>
                        )}
                      </div>

                      {selected === entry && (
                        <div className="rounded-lg border border-line px-3 py-2 text-[11px] text-text-muted">
                          <span className="font-semibold text-electric">Metadata: </span>
                          test_id={entry.test_id}, scenario={entry.scenario_id}, category=
                          {entry.category}, attack_level={entry.attack_level ?? 'none'}
                        </div>
                      )}
                      <button
                        onClick={() => setSelected(selected === entry ? null : entry)}
                        className="self-start text-[11px] text-signal-hover hover:text-signal"
                      >
                        {selected === entry ? 'Hide details' : 'Show details'}
                      </button>
                    </div>
                  </Card>
                )
              })}
            </div>
          </PageSection>
        ) : suite && suite.entries.length === 0 ? (
          <EmptyState
            icon="🔇"
            title="No recordings in this manifest"
            description="The manifest for this benchmark is empty. Generate a suite in Scenario Lab first."
          />
        ) : null}

        {transcripts.size === 0 && state === 'ready' && (
          <PageSection title="Missing audio state">
            <EmptyState
              icon="🔇"
              title="No transcription available"
              description="When STT transcription is unavailable for a recording, this state appears instead of fabricated text."
            />
          </PageSection>
        )}
      </div>
    </PageShell>
  )
}
