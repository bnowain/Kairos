import { apiFetch } from './client'
import type { Clip } from './types'

export interface ClipsListParams {
  item_id?: string
  status?: string
  clip_source?: 'ai' | 'manual'
  min_score?: number
  page?: number
  page_size?: number
}

export interface ClipsListResponse {
  items: Clip[]
  total: number
  page: number
  page_size: number
}

export function fetchClips(params: ClipsListParams = {}): Promise<ClipsListResponse> {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) qs.set(k, String(v))
  })
  const query = qs.toString()
  return apiFetch<ClipsListResponse>(`/api/clips${query ? `?${query}` : ''}`)
}

export function fetchClip(clipId: string): Promise<Clip> {
  return apiFetch<Clip>(`/api/clips/${clipId}`)
}

export function generateClips(itemId: string): Promise<{ clips_created: number; job_id: string }> {
  return apiFetch('/api/clips/generate', {
    method: 'POST',
    body: JSON.stringify({ item_id: itemId }),
  })
}

export function extractClip(clipId: string): Promise<{ status: string }> {
  return apiFetch(`/api/clips/${clipId}/extract`, { method: 'POST' })
}

export function batchExtractClips(clipIds?: string[]): Promise<{ queued: number }> {
  return apiFetch('/api/clips/batch/extract', {
    method: 'POST',
    body: JSON.stringify({ clip_ids: clipIds }),
  })
}

export function deleteClip(clipId: string): Promise<{ status: string }> {
  return apiFetch(`/api/clips/${clipId}`, { method: 'DELETE' })
}
