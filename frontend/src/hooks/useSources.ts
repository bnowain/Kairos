import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchSources, createSource, updateSource, deleteSource, pollSource } from '../api/sources'
import type { CreateSourceBody, UpdateSourceBody } from '../api/sources'
import { toast } from '../store/useToastStore'

export function useSources() {
  return useQuery({
    queryKey: ['sources'],
    queryFn: fetchSources,
  })
}

export function useCreateSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateSourceBody) => createSource(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['sources'] })
      toast.success('Source created')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}

export function useUpdateSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sourceId, body }: { sourceId: string; body: UpdateSourceBody }) =>
      updateSource(sourceId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['sources'] })
      toast.success('Source updated')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}

export function useDeleteSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sourceId: string) => deleteSource(sourceId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['sources'] })
      toast.success('Source deleted')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}

export function usePollSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sourceId: string) => pollSource(sourceId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['sources'] })
      toast.info('Polling source...')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
  })
}
