import { apiFetch } from './client'
import type { CaptionStyle } from './types'

export function fetchCaptionStyles(): Promise<CaptionStyle[]> {
  return apiFetch<CaptionStyle[]>('/api/captions/styles')
}

export function fetchCaptionStyle(styleId: string): Promise<CaptionStyle> {
  return apiFetch<CaptionStyle>(`/api/captions/styles/${styleId}`)
}

export function createCaptionStyle(
  style: Omit<CaptionStyle, 'style_id' | 'created_at'>,
): Promise<CaptionStyle> {
  return apiFetch<CaptionStyle>('/api/captions/styles', {
    method: 'POST',
    body: JSON.stringify(style),
  })
}

export function deleteCaptionStyle(styleId: string): Promise<{ status: string }> {
  return apiFetch(`/api/captions/styles/${styleId}`, { method: 'DELETE' })
}
