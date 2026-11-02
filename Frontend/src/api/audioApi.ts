/**
 * Real audio data (api/server.py):
 * - GET /api/manifest/{id}  -> manifest entries with actual audio paths
 * - GET /api/audio?path=    -> streams the file (recordings / attacked / responses)
 */
import type { ManifestItem } from './client'
import { apiGet, audioUrl } from './client'

export interface AudioEntry {
  test_id: string
  scenario_id: string
  category: string
  scenario_type: string
  language: string
  condition: 'clean' | 'attacked'
  attack_type: string | null
  attack_level: string | null
  /** Absolute backend path; only real files, always present for real runs. */
  audio_path: string
  /** Streamable URL for <audio>. */
  src: string
}

export interface AudioSuite {
  benchmarkId: string
  label: string
  entries: AudioEntry[]
}

export async function fetchAudioSuite(benchmarkId: string): Promise<AudioSuite> {
  const manifest = await apiGet<{ items: ManifestItem[] }>(
    `/api/manifest/${encodeURIComponent(benchmarkId)}`,
  )
  const entries: AudioEntry[] = (manifest.items ?? []).map((item) => ({
    test_id: item.test_id,
    scenario_id: item.scenario_id,
    category: item.category,
    scenario_type: item.scenario_type,
    language: item.language,
    condition: item.condition,
    attack_type: item.attack_type,
    attack_level: item.attack_level,
    audio_path: item.audio_path,
    src: audioUrl(item.audio_path),
  }))
  return {
    benchmarkId,
    label: benchmarkId,
    entries,
  }
}

export function hasPlayableAudio(entry: AudioEntry): boolean {
  return Boolean(entry.src && entry.audio_path)
}
