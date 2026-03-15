import { apiFetch } from './client'
import type { AcquisitionSource } from './types'

export interface CreateSourceBody {
  source_type: string
  source_url: string
  source_name?: string
  platform: string
  schedule_cron?: string
  enabled?: number
  download_quality?: string
}

export interface UpdateSourceBody {
  source_name?: string
  schedule_cron?: string
  enabled?: number
  download_quality?: string
}

export function fetchSources(): Promise<AcquisitionSource[]> {
  return apiFetch<AcquisitionSource[]>('/api/acquisition/sources')
}

export function createSource(body: CreateSourceBody): Promise<AcquisitionSource> {
  return apiFetch<AcquisitionSource>('/api/acquisition/sources', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateSource(sourceId: string, body: UpdateSourceBody): Promise<AcquisitionSource> {
  return apiFetch<AcquisitionSource>(`/api/acquisition/sources/${sourceId}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function deleteSource(sourceId: string): Promise<{ status: string }> {
  return apiFetch(`/api/acquisition/sources/${sourceId}`, { method: 'DELETE' })
}

export function pollSource(sourceId: string): Promise<{ status: string }> {
  return apiFetch(`/api/acquisition/sources/${sourceId}/poll`, { method: 'POST' })
}
