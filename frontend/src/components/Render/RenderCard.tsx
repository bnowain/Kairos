import { Download, RefreshCw } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Progress } from '../ui/Progress'
import { Button } from '../ui/Button'
import { apiUrl } from '../../api/client'
import { formatDateTime } from '../../utils/format'
import { useRetryRenderJob } from '../../hooks/useRender'
import type { RenderJob } from '../../api/types'

interface RenderCardProps {
  job: RenderJob
  timelineName?: string
}

const statusVariant: Record<string, 'default' | 'info' | 'success' | 'error' | 'warning'> = {
  queued: 'default',
  running: 'info',
  done: 'success',
  error: 'error',
}

export function RenderCard({ job, timelineName }: RenderCardProps) {
  const { mutate: retry, isPending } = useRetryRenderJob()

  const isRunning = job.render_status === 'running'
  const isDone = job.render_status === 'done'
  const isError = job.render_status === 'error'
  const outputFilename = job.output_path?.split('/').pop()

  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-100 truncate">
            {timelineName ?? job.timeline_id.slice(0, 8)}
          </p>
          <p className="text-xs text-gray-500 font-mono mt-0.5">
            {job.render_id.slice(0, 12)}...
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant={job.render_quality === 'final' ? 'success' : 'secondary'}>
            {job.render_quality.toUpperCase()}
          </Badge>
          <Badge variant={statusVariant[job.render_status] ?? 'default'}>
            {job.render_status}
          </Badge>
        </div>
      </div>

      {isRunning && <Progress value={50} className="animate-pulse" />}

      <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
        {job.encoder && (
          <span>Encoder: <span className="text-gray-400">{job.encoder}</span></span>
        )}
        {job.started_at && (
          <span>Started: <span className="text-gray-400">{formatDateTime(job.started_at)}</span></span>
        )}
        {job.completed_at && (
          <span>Completed: <span className="text-gray-400">{formatDateTime(job.completed_at)}</span></span>
        )}
      </div>

      {isError && job.error_msg && (
        <p className="text-xs text-red-400 bg-red-950/30 rounded px-2 py-1">
          {job.error_msg}
        </p>
      )}

      <div className="flex gap-2 justify-end">
        {isDone && outputFilename && (
          <a href={apiUrl(`/media/renders/${outputFilename}`)} download>
            <Button size="sm" variant="secondary">
              <Download className="h-3.5 w-3.5" />
              Download
            </Button>
          </a>
        )}
        {isError && (
          <Button
            size="sm"
            variant="outline"
            loading={isPending}
            onClick={() => retry(job.render_id)}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </Button>
        )}
      </div>
    </div>
  )
}
