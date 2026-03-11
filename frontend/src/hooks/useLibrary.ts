import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchLibrary, fetchMediaItem, downloadVideo, deleteMediaItem } from '../api/library'
import type { LibraryListParams } from '../api/library'

const TERMINAL_STATUSES = new Set(['ready', 'error'])

export function useLibrary(params: LibraryListParams = {}) {
  return useQuery({
    queryKey: ['library', params],
    queryFn: () => fetchLibrary(params),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 3000
      const hasActive = data.items.some((item) => !TERMINAL_STATUSES.has(item.item_status))
      return hasActive ? 3000 : false
    },
  })
}

export function useMediaItem(itemId: string) {
  return useQuery({
    queryKey: ['media-item', itemId],
    queryFn: () => fetchMediaItem(itemId),
    refetchInterval: (query) => {
      const item = query.state.data
      if (!item) return 3000
      return TERMINAL_STATUSES.has(item.item_status) ? false : 3000
    },
    enabled: !!itemId,
  })
}

export function useDownloadVideo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (url: string) => downloadVideo(url),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['library'] })
    },
  })
}

export function useDeleteMediaItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => deleteMediaItem(itemId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['library'] })
    },
  })
}
