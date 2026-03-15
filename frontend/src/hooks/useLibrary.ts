import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { fetchLibrary, fetchMediaItem, downloadVideo, deleteMediaItem, uploadVideo } from '../api/library'
import type { LibraryListParams } from '../api/library'
import { toast } from '../store/useToastStore'

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
      toast.success('Video download started')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}

export function useDeleteMediaItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => deleteMediaItem(itemId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['library'] })
      toast.success('Item deleted')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}

export function useUploadVideo() {
  const qc = useQueryClient()
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const upload = useCallback(
    async (file: File, title?: string) => {
      setIsUploading(true)
      setUploadProgress(0)
      setUploadError(null)
      try {
        const result = await uploadVideo(file, title, setUploadProgress)
        void qc.invalidateQueries({ queryKey: ['library'] })
        toast.success('Video uploaded successfully')
        return result
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        setUploadError(msg)
        throw err
      } finally {
        setIsUploading(false)
      }
    },
    [qc],
  )

  return { upload, uploadProgress, isUploading, uploadError }
}
