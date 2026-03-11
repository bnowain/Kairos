import { apiFetch } from './client'
import type { MediaItem } from './types'

export interface LibraryListParams {
  page?: number
  page_size?: number
  status?: string
  platform?: string
  q?: string
}

export interface LibraryListResponse {
  items: MediaItem[]
  total: number
  page: number
  page_size: number
}

export function fetchLibrary(params: LibraryListParams = {}): Promise<LibraryListResponse> {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.status) qs.set('status', params.status)
  if (params.platform) qs.set('platform', params.platform)
  if (params.q) qs.set('q', params.q)
  const query = qs.toString()
  return apiFetch<LibraryListResponse>(`/api/library${query ? `?${query}` : ''}`)
}

export function fetchMediaItem(itemId: string): Promise<MediaItem> {
  return apiFetch<MediaItem>(`/api/library/${itemId}`)
}

export function downloadVideo(url: string): Promise<{ item_id: string; status: string }> {
  return apiFetch('/api/acquisition/download', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

export function deleteMediaItem(itemId: string): Promise<{ status: string }> {
  return apiFetch(`/api/library/${itemId}`, { method: 'DELETE' })
}

export function uploadVideo(
  file: File,
  title?: string,
  onProgress?: (pct: number) => void,
): Promise<{ item_id: string; status: string; message: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append('file', file)
    if (title) formData.append('title', title)

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    })
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as { item_id: string; status: string; message: string })
      } else {
        reject(new Error(`Upload failed ${xhr.status}: ${xhr.responseText}`))
      }
    })
    xhr.addEventListener('error', () => reject(new Error('Upload network error')))
    xhr.open('POST', 'http://localhost:8400/api/acquisition/upload')
    xhr.send(formData)
  })
}
