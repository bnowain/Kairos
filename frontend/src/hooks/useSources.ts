import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchSources, createSource, updateSource, deleteSource, pollSource } from '../api/sources'
import type { CreateSourceBody, UpdateSourceBody } from '../api/sources'

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
    },
  })
}

export function useUpdateSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sourceId, body }: { sourceId: string; body: UpdateSourceBody }) =>
      updateSource(sourceId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useDeleteSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sourceId: string) => deleteSource(sourceId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function usePollSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sourceId: string) => pollSource(sourceId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}
