import { apiFetch } from './client'

export interface QuickJobIn {
  urls: string[]
  template_id: string
  caption_style_id?: string | null
  aspect_ratio: '9:16' | '16:9' | '1:1'
}

export interface QuickJobOut {
  job_id: string
  urls: string[]
  template_id: string | null
  aspect_ratio: string
  job_status: string
  stage_label: string | null
  progress: number
  item_ids: string[] | null
  timeline_id: string | null
  render_id: string | null
  output_path: string | null
  error_msg: string | null
  created_at: string
  updated_at: string
}

export function createQuickJob(req: QuickJobIn): Promise<QuickJobOut> {
  return apiFetch('/api/jobs/quick', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function getQuickJob(jobId: string): Promise<QuickJobOut> {
  return apiFetch(`/api/jobs/${jobId}`)
}

export function listQuickJobs(): Promise<QuickJobOut[]> {
  return apiFetch('/api/jobs')
}

export function retryQuickJob(jobId: string): Promise<QuickJobOut> {
  return apiFetch(`/api/jobs/${jobId}/retry`, { method: 'POST' })
}

export function cancelQuickJob(jobId: string): Promise<{ cancelled: boolean }> {
  return apiFetch(`/api/jobs/${jobId}`, { method: 'DELETE' })
}

export function downloadQuickJobUrl(jobId: string): string {
  return `http://localhost:8400/api/jobs/${jobId}/download`
}
