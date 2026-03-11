import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchClips, generateClips, extractClip, batchExtractClips } from '../api/clips'
import type { ClipsListParams } from '../api/clips'

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
    },
  })
}

export function useBatchExtractClips() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (clipIds?: string[]) => batchExtractClips(clipIds),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['clips'] })
    },
  })
}
