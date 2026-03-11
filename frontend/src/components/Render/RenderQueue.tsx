import { RenderCard } from './RenderCard'
import { Spinner } from '../ui/Spinner'
import type { RenderJob } from '../../api/types'

interface RenderQueueProps {
  jobs: RenderJob[]
  isLoading: boolean
  error?: Error | null
}

export function RenderQueue({ jobs, isLoading, error }: RenderQueueProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-red-400">
        <p>Failed to load render jobs</p>
        <p className="text-sm text-gray-500">{error.message}</p>
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-500">
        <p>No render jobs. Click New Render to start.</p>
      </div>
    )
  }

  return (
    <div data-testid="render-queue" className="flex flex-col gap-3">
      {jobs.map((job) => (
        <RenderCard key={job.render_id} job={job} />
      ))}
    </div>
  )
}
