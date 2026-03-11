import { apiFetch } from './client'
import type { TranscriptionJob, TranscriptionSegment } from './types'

export function startTranscription(
  itemId: string,
  opts: { model?: string; language?: string; diarize?: boolean } = {},
): Promise<TranscriptionJob> {
  return apiFetch('/api/transcription/jobs', {
    method: 'POST',
    body: JSON.stringify({ item_id: itemId, ...opts }),
  })
}

export function fetchTranscriptionJob(jobId: string): Promise<TranscriptionJob> {
  return apiFetch<TranscriptionJob>(`/api/transcription/jobs/${jobId}`)
}

export function fetchTranscriptionJobs(itemId?: string): Promise<TranscriptionJob[]> {
  const qs = itemId ? `?item_id=${itemId}` : ''
  return apiFetch<TranscriptionJob[]>(`/api/transcription/jobs${qs}`)
}

export function fetchSegments(itemId: string): Promise<TranscriptionSegment[]> {
  return apiFetch<TranscriptionSegment[]>(`/api/transcription/segments/${itemId}`)
}

export function exportTranscript(
  itemId: string,
  format: 'srt' | 'vtt' | 'json',
): Promise<Blob> {
  return fetch(`http://localhost:8400/api/transcription/export/${itemId}?format=${format}`).then(
    (r) => r.blob(),
  )
}
