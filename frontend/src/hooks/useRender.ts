import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchRenderJobs, fetchRenderJob, createRenderJob, retryRenderJob } from '../api/render'
import type { CreateRenderParams } from '../api/render'

export function useRenderJobs() {
  return useQuery({
    queryKey: ['render-jobs'],
    queryFn: fetchRenderJobs,
    refetchInterval: (query) => {
      const jobs = query.state.data
      if (!jobs) return false
      const hasActive = jobs.some((j) => j.render_status === 'queued' || j.render_status === 'running')
      return hasActive ? 3000 : false
    },
  })
}

export function useCreateRenderJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: CreateRenderParams) => createRenderJob(params),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['render-jobs'] })
    },
  })
}

export function useRenderJob(renderId: string) {
  return useQuery({
    queryKey: ['render-job', renderId],
    queryFn: () => fetchRenderJob(renderId),
    enabled: !!renderId,
    refetchInterval: (query) => {
      const job = query.state.data
      if (!job) return false
      return job.render_status === 'running' ? 2000 : false
    },
  })
}

export function useRetryRenderJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (renderId: string) => retryRenderJob(renderId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['render-jobs'] })
    },
  })
}
