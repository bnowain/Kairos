import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Download, RotateCcw, XCircle, Plus, Clock,
  CheckCircle2, AlertCircle, Loader2, Ban,
} from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { Button } from '../components/ui/Button'
import { Progress } from '../components/ui/Progress'
import { Spinner } from '../components/ui/Spinner'
import {
  listQuickJobs, retryQuickJob, cancelQuickJob, downloadQuickJobUrl,
} from '../api/jobs'
import type { QuickJobOut } from '../api/jobs'

const STATUS_CONFIG: Record<string, { color: string; bg: string; icon: typeof CheckCircle2 }> = {
  queued:       { color: 'text-gray-400',   bg: 'bg-gray-500/20',   icon: Clock },
  downloading:  { color: 'text-blue-400',   bg: 'bg-blue-500/20',   icon: Loader2 },
  transcribing: { color: 'text-purple-400', bg: 'bg-purple-500/20', icon: Loader2 },
  analyzing:    { color: 'text-yellow-400', bg: 'bg-yellow-500/20', icon: Loader2 },
  generating:   { color: 'text-orange-400', bg: 'bg-orange-500/20', icon: Loader2 },
  rendering:    { color: 'text-teal-400',   bg: 'bg-teal-500/20',   icon: Loader2 },
  done:         { color: 'text-green-400',  bg: 'bg-green-500/20',  icon: CheckCircle2 },
  error:        { color: 'text-red-400',    bg: 'bg-red-500/20',    icon: AlertCircle },
  cancelled:    { color: 'text-gray-500',   bg: 'bg-gray-500/20',   icon: Ban },
}

function isRunning(status: string) {
  return !['done', 'error', 'cancelled'].includes(status)
}

function formatTime(iso: string) {
  try {
    const d = new Date(iso + 'Z')
    return d.toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function JobCard({ job }: { job: QuickJobOut }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const cfg = STATUS_CONFIG[job.job_status] ?? STATUS_CONFIG.queued
  const Icon = cfg.icon
  const running = isRunning(job.job_status)

  const retryMut = useMutation({
    mutationFn: () => retryQuickJob(job.job_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['quickJobs'] }),
  })

  const cancelMut = useMutation({
    mutationFn: () => cancelQuickJob(job.job_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['quickJobs'] }),
  })

  const handleShare = async () => {
    const url = downloadQuickJobUrl(job.job_id)
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Kairos Video', url })
      } catch { /* user cancelled share */ }
    } else {
      await navigator.clipboard.writeText(url)
    }
  }

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/60 p-4 flex flex-col gap-3">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`w-8 h-8 rounded-full ${cfg.bg} flex items-center justify-center shrink-0`}>
            <Icon className={`w-4 h-4 ${cfg.color} ${running ? 'animate-spin' : ''}`} />
          </div>
          <div className="min-w-0">
            <p className={`text-sm font-semibold ${cfg.color} capitalize`}>
              {job.job_status}
            </p>
            <p className="text-xs text-gray-500 truncate">
              {job.stage_label ?? job.job_status}
            </p>
          </div>
        </div>
        <span className="text-xs text-gray-600 shrink-0">
          {formatTime(job.created_at)}
        </span>
      </div>

      {/* URLs */}
      {job.urls.length > 0 && (
        <div className="flex flex-col gap-0.5">
          {job.urls.map((url, i) => (
            <p key={i} className="text-xs text-gray-400 truncate" title={url}>
              {url}
            </p>
          ))}
        </div>
      )}

      {/* Metadata chips */}
      <div className="flex flex-wrap gap-1.5">
        {job.template_id && (
          <span className="text-[10px] px-2 py-0.5 rounded-full border border-gray-700 text-gray-400">
            {job.template_id}
          </span>
        )}
        <span className="text-[10px] px-2 py-0.5 rounded-full border border-gray-700 text-gray-400">
          {job.aspect_ratio}
        </span>
      </div>

      {/* Progress bar for running jobs */}
      {running && (
        <div className="flex items-center gap-2">
          <Progress value={job.progress} className="h-1.5 flex-1" />
          <span className="text-xs text-gray-500 w-8 text-right">{job.progress}%</span>
        </div>
      )}

      {/* Error message */}
      {job.job_status === 'error' && job.error_msg && (
        <p className="text-xs text-red-400/80 line-clamp-2">{job.error_msg}</p>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 mt-1">
        {job.job_status === 'done' && job.output_path && (
          <>
            <a
              href={downloadQuickJobUrl(job.job_id)}
              download
              className="flex items-center gap-1.5 rounded-md bg-green-600 hover:bg-green-500 px-3 py-1.5 text-xs font-medium text-white transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Download
            </a>
            <button
              onClick={handleShare}
              className="flex items-center gap-1.5 rounded-md border border-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-800 transition-colors"
            >
              Share
            </button>
          </>
        )}
        {(job.job_status === 'error' || job.job_status === 'done' || job.job_status === 'cancelled') && (
          <button
            onClick={() => retryMut.mutate()}
            disabled={retryMut.isPending}
            className="flex items-center gap-1.5 rounded-md border border-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Retry
          </button>
        )}
        {running && (
          <button
            onClick={() => cancelMut.mutate()}
            disabled={cancelMut.isPending}
            className="flex items-center gap-1.5 rounded-md border border-red-800/50 px-3 py-1.5 text-xs text-red-400 hover:bg-red-900/20 transition-colors disabled:opacity-50"
          >
            <XCircle className="w-3.5 h-3.5" />
            Cancel
          </button>
        )}
        {running && (
          <button
            onClick={() => navigate(`/quick?job_id=${job.job_id}`)}
            className="flex items-center gap-1.5 rounded-md border border-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-800 transition-colors ml-auto"
          >
            View
          </button>
        )}
      </div>
    </div>
  )
}

export default function JobHistoryPage() {
  const navigate = useNavigate()
  const { data: jobs, isLoading } = useQuery({
    queryKey: ['quickJobs'],
    queryFn: listQuickJobs,
    refetchInterval: 5000,
  })

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title="Job History"
        actions={
          <Button
            size="sm"
            onClick={() => navigate('/quick')}
            className="flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            New Job
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-4 md:p-6 flex flex-col gap-3">
          {isLoading && (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          )}
          {!isLoading && jobs?.length === 0 && (
            <div className="flex flex-col items-center gap-3 py-12 text-gray-500">
              <Clock className="w-8 h-8" />
              <p className="text-sm">No jobs yet</p>
              <Button size="sm" onClick={() => navigate('/quick')}>
                Create your first job
              </Button>
            </div>
          )}
          {jobs?.map(job => <JobCard key={job.job_id} job={job} />)}
        </div>
      </div>
    </div>
  )
}
