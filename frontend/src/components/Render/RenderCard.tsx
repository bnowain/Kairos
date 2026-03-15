import { useState } from 'react'
import { Download, RefreshCw, Play, Clock, ListOrdered } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Progress } from '../ui/Progress'
import { Button } from '../ui/Button'
import { RenderPreview } from './RenderPreview'
import { apiUrl } from '../../api/client'
import { formatDateTime } from '../../utils/format'
import { useRetryRenderJob } from '../../hooks/useRender'
import type { RenderJob } from '../../api/types'

interface RenderCardProps {
  job: RenderJob
  timelineName?: string
  queuePosition?: number
}

const statusVariant: Record<string, 'default' | 'info' | 'success' | 'error' | 'warning'> = {
  queued: 'default',
  running: 'info',
  done: 'success',
  error: 'error',
}

function useElapsedTime(startedAt: string | null, completedAt: string | null, isRunning: boolean) {
  const [now, setNow] = useState(Date.now())

  // Refresh every second while running
  useState(() => {
    if (!isRunning) return
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  })

  if (!startedAt) return null

  const start = new Date(startedAt).getTime()
  const end = completedAt ? new Date(completedAt).getTime() : now
  const seconds = Math.floor((end - start) / 1000)
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${String(secs).padStart(2, '0')}`
}

export function RenderCard({ job, timelineName, queuePosition }: RenderCardProps) {
  const { mutate: retry, isPending } = useRetryRenderJob()
  const [showPreview, setShowPreview] = useState(false)

  const isRunning = job.render_status === 'running'
  const isDone = job.render_status === 'done'
  const isError = job.render_status === 'error'
  const isQueued = job.render_status === 'queued'
  const outputFilename = job.output_path?.split('/').pop()

  const elapsed = useElapsedTime(job.started_at, job.completed_at, isRunning)

  // Heuristic progress: ~5s/element preview, ~15s/element final
  const elementCount = job.render_params
    ? (JSON.parse(job.render_params) as { element_count?: number }).element_count ?? 5
    : 5
  const estTotalSec = elementCount * (job.render_quality === 'final' ? 15 : 5)
  const elapsedSec = job.started_at
    ? (Date.now() - new Date(job.started_at).getTime()) / 1000
    : 0
  const progressPct = isRunning ? Math.min(Math.round((elapsedSec / estTotalSec) * 100), 95) : 0

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

      {isRunning && (
        <div className="space-y-1.5">
          <Progress value={progressPct} />
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {elapsed ?? '0:00'}
            </span>
            <span>Encoding... ~{progressPct}%</span>
          </div>
        </div>
      )}

      {isQueued && queuePosition !== undefined && (
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <ListOrdered className="h-3 w-3" />
          Position {queuePosition} in queue
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
        {job.encoder && (
          <span>Encoder: <span className="text-gray-400">{job.encoder}</span></span>
        )}
        {job.started_at && (
          <span>Started: <span className="text-gray-400">{formatDateTime(job.started_at)}</span></span>
        )}
        {isDone && job.completed_at && job.started_at && (
          <span>Render time: <span className="text-gray-400">{elapsed}</span></span>
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
          <>
            <Button size="sm" variant="secondary" onClick={() => setShowPreview(true)}>
              <Play className="h-3.5 w-3.5" />
              Play
            </Button>
            <a href={apiUrl(`/media/renders/${outputFilename}`)} download>
              <Button size="sm" variant="secondary">
                <Download className="h-3.5 w-3.5" />
                Download
              </Button>
            </a>
          </>
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

      {isDone && job.output_path && (
        <RenderPreview
          open={showPreview}
          onOpenChange={setShowPreview}
          renderId={job.render_id}
          outputPath={job.output_path}
        />
      )}
    </div>
  )
}
