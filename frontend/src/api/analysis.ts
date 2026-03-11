import { apiFetch } from './client'
import type { AnalysisScore, AnalysisHighlight } from './types'

export function startAnalysis(itemId: string): Promise<{ job_id: string; status: string }> {
  return apiFetch('/api/analysis/jobs', {
    method: 'POST',
    body: JSON.stringify({ item_id: itemId }),
  })
}

export function fetchScores(itemId: string): Promise<AnalysisScore[]> {
  return apiFetch<AnalysisScore[]>(`/api/analysis/scores/${itemId}`)
}

export function fetchHighlights(itemId: string, limit = 10): Promise<AnalysisHighlight[]> {
  return apiFetch<AnalysisHighlight[]>(
    `/api/analysis/highlights/${itemId}?limit=${limit}`,
  )
}
