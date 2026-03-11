import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchSegments,
  fetchTranscriptionJobs,
  startTranscription,
} from '../api/transcription'

export function useSegments(itemId: string) {
  return useQuery({
    queryKey: ['segments', itemId],
    queryFn: () => fetchSegments(itemId),
    enabled: !!itemId,
  })
}

export function useTranscriptionJobs(itemId?: string) {
  return useQuery({
    queryKey: ['transcription-jobs', itemId],
    queryFn: () => fetchTranscriptionJobs(itemId),
    refetchInterval: (query) => {
      const jobs = query.state.data
      if (!jobs) return 3000
      const hasActive = jobs.some((j) => j.job_status === 'queued' || j.job_status === 'running')
      return hasActive ? 3000 : false
    },
  })
}

export function useStartTranscription() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      itemId,
      opts,
    }: {
      itemId: string
      opts?: { model?: string; language?: string; diarize?: boolean }
    }) => startTranscription(itemId, opts),
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ['transcription-jobs', variables.itemId] })
      void qc.invalidateQueries({ queryKey: ['media-item', variables.itemId] })
    },
  })
}
