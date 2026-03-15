import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchClips, generateClips, extractClip, batchExtractClips, createClip, deleteClip } from '../api/clips'
import type { ClipsListParams } from '../api/clips'
import { toast } from '../store/useToastStore'

export function useClips(params: ClipsListParams = {}) {
  return useQuery({
    queryKey: ['clips', params],
    queryFn: () => fetchClips(params),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return false
      const hasActive = data.items.some(
        (c) => c.clip_status === 'extracting' || c.clip_status === 'pending',
      )
      return hasActive ? 3000 : false
    },
  })
}

export function useGenerateClips() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => generateClips(itemId),
    onSuccess: (_data, itemId) => {
      void qc.invalidateQueries({ queryKey: ['clips', { item_id: itemId }] })
      void qc.invalidateQueries({ queryKey: ['clips'] })
      void qc.invalidateQueries({ queryKey: ['media-item', itemId] })
    },
  })
}

export function useExtractClip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (clipId: string) => extractClip(clipId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['clips'] })
      toast.info('Clip extraction started')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}

export function useBatchExtractClips() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (clipIds?: string[]) => batchExtractClips(clipIds),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['clips'] })
      toast.info('Batch extraction started')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}

export function useCreateClip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      item_id: string
      start_ms: number
      end_ms: number
      clip_title?: string
      remove_silence?: boolean
    }) => createClip(body),
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ['clips', { item_id: variables.item_id }] })
      void qc.invalidateQueries({ queryKey: ['clips'] })
      void qc.invalidateQueries({ queryKey: ['media-item', variables.item_id] })
      toast.success('Clip created')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}

export function useDeleteClip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (clipId: string) => deleteClip(clipId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['clips'] })
      toast.success('Clip deleted')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}

export function useBulkDeleteClips() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (clipIds: string[]) => Promise.all(clipIds.map((id) => deleteClip(id))),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['clips'] })
      toast.success('Clips deleted')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}
