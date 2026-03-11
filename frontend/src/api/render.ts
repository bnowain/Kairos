import { apiFetch } from './client'
import type { RenderJob } from './types'

export interface CreateRenderParams {
  timeline_id: string
  render_quality: 'preview' | 'final'
  add_captions?: boolean
  caption_style_id?: string
  aspect_ratio?: string
}

export function fetchRenderJobs(): Promise<RenderJob[]> {
  return apiFetch<RenderJob[]>('/api/render/jobs')
}

export function fetchRenderJob(renderId: string): Promise<RenderJob> {
  return apiFetch<RenderJob>(`/api/render/jobs/${renderId}`)
}

export function createRenderJob(params: CreateRenderParams): Promise<RenderJob> {
  return apiFetch<RenderJob>('/api/render/jobs', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export function retryRenderJob(renderId: string): Promise<RenderJob> {
  return apiFetch<RenderJob>(`/api/render/jobs/${renderId}/retry`, { method: 'POST' })
}
