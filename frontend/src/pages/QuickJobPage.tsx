import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Trash2, Zap, ChevronRight, Download, AlertCircle } from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Progress } from '../components/ui/Progress'
import { Spinner } from '../components/ui/Spinner'
import { fetchTemplates } from '../api/stories'
import { fetchCaptionStyles } from '../api/captions'
import { createQuickJob, getQuickJob } from '../api/jobs'
import type { QuickJobOut } from '../api/jobs'

type AspectRatio = '9:16' | '16:9' | '1:1'

const ASPECT_OPTIONS: { value: AspectRatio; label: string; sub: string }[] = [
  { value: '9:16', label: '9:16', sub: 'TikTok / Reels' },
  { value: '16:9', label: '16:9', sub: 'YouTube' },
  { value: '1:1',  label: '1:1',  sub: 'Square' },
]

const STATUS_COLORS: Record<string, string> = {
  queued:       'text-gray-400',
  downloading:  'text-blue-400',
  transcribing: 'text-purple-400',
  analyzing:    'text-yellow-400',
  generating:   'text-orange-400',
  rendering:    'text-teal-400',
  done:         'text-green-400',
  error:        'text-red-400',
}

// ── Progress polling hook ─────────────────────────────────────────────────────

function useJobPoller(jobId: string | null) {
  const [job, setJob] = useState<QuickJobOut | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!jobId) return

    const poll = async () => {
      try {
        const data = await getQuickJob(jobId)
        setJob(data)
        if (data.job_status === 'done' || data.job_status === 'error') {
          if (intervalRef.current) clearInterval(intervalRef.current)
        }
      } catch {
        // keep polling on transient errors
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 3000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [jobId])

  return job
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function QuickJobPage() {
  const [urls, setUrls] = useState<string[]>([''])
  const [templateId, setTemplateId] = useState<string>('')
  const [captionStyleId, setCaptionStyleId] = useState<string | null>(null)
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('9:16')
  const [jobId, setJobId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const job = useJobPoller(jobId)

  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: fetchTemplates,
  })

  const { data: captionStyles = [] } = useQuery({
    queryKey: ['captionStyles'],
    queryFn: fetchCaptionStyles,
  })

  // Auto-select first template
  useEffect(() => {
    if (templates.length > 0 && !templateId) {
      setTemplateId(templates[0].template_id)
    }
  }, [templates, templateId])

  const addUrl = () => setUrls(u => [...u, ''])
  const removeUrl = (i: number) => setUrls(u => u.filter((_, idx) => idx !== i))
  const updateUrl = (i: number, val: string) =>
    setUrls(u => u.map((v, idx) => (idx === i ? val : v)))

  const validUrls = urls.filter(u => u.trim().length > 0)
  const canSubmit = validUrls.length > 0 && templateId && !submitting

  const handleRun = async () => {
    if (!canSubmit) return
    setSubmitError(null)
    setSubmitting(true)
    try {
      const result = await createQuickJob({
        urls: validUrls,
        template_id: templateId,
        caption_style_id: captionStyleId ?? undefined,
        aspect_ratio: aspectRatio,
      })
      setJobId(result.job_id)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to start job')
      setSubmitting(false)
    }
  }

  const handleReset = () => {
    setJobId(null)
    setSubmitting(false)
    setSubmitError(null)
    setUrls([''])
  }

  // ── Progress screen ───────────────────────────────────────────────────────
  if (jobId) {
    const statusColor = STATUS_COLORS[job?.job_status ?? 'queued'] ?? 'text-gray-400'
    const isDone  = job?.job_status === 'done'
    const isError = job?.job_status === 'error'

    return (
      <div className="flex flex-col h-full overflow-hidden">
        <TopBar title="Quick Job" />
        <div className="flex-1 flex flex-col items-center justify-center gap-6 p-6">
          <div className="w-full max-w-md flex flex-col gap-4">
            {/* Status indicator */}
            <div className="flex flex-col items-center gap-2 text-center">
              {!isDone && !isError && <Spinner size="lg" />}
              {isDone && (
                <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-green-400" />
                </div>
              )}
              {isError && (
                <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center">
                  <AlertCircle className="w-6 h-6 text-red-400" />
                </div>
              )}
              <p className={`text-sm font-semibold ${statusColor}`}>
                {job?.stage_label ?? 'Starting…'}
              </p>
            </div>

            {/* Progress bar */}
            <Progress value={job?.progress ?? 0} className="h-2" />
            <p className="text-xs text-gray-500 text-center">{job?.progress ?? 0}%</p>

            {/* Error message */}
            {isError && job?.error_msg && (
              <div className="rounded-md bg-red-900/30 border border-red-700/50 p-3 text-xs text-red-300">
                {job.error_msg}
              </div>
            )}

            {/* Download button when done */}
            {isDone && job?.output_path && (
              <a
                href={`http://localhost:8400/media/${job.output_path}`}
                download
                className="flex items-center justify-center gap-2 rounded-md bg-green-600 hover:bg-green-500 px-4 py-2.5 text-sm font-medium text-white transition-colors"
              >
                <Download className="w-4 h-4" />
                Download video
              </a>
            )}
            {isDone && !job?.output_path && (
              <p className="text-sm text-gray-400 text-center">
                Timeline generated — open Render Queue to download.
              </p>
            )}

            {/* Action buttons */}
            <div className="flex gap-2 mt-2">
              {(isDone || isError) && (
                <Button variant="secondary" className="flex-1" onClick={handleReset}>
                  Start new job
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Input form ────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Quick Job" />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-lg mx-auto p-4 md:p-6 flex flex-col gap-6">

          {/* URL inputs */}
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
              Video URLs
            </h2>
            {urls.map((url, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input
                  value={url}
                  onChange={e => updateUrl(i, e.target.value)}
                  placeholder="https://youtube.com/watch?v=…"
                  className="flex-1"
                />
                {urls.length > 1 && (
                  <button
                    onClick={() => removeUrl(i)}
                    className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
            <button
              onClick={addUrl}
              className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors w-fit"
            >
              <Plus className="w-3.5 h-3.5" />
              Add another URL
            </button>
          </section>

          {/* Template selector */}
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
              Template
            </h2>
            {templatesLoading ? (
              <Spinner size="sm" />
            ) : (
              <div className="flex flex-col gap-2">
                {templates.map(t => (
                  <button
                    key={t.template_id}
                    onClick={() => setTemplateId(t.template_id)}
                    className={`flex items-center justify-between rounded-lg border px-4 py-3 text-left transition-colors ${
                      templateId === t.template_id
                        ? 'border-blue-500 bg-blue-600/10 text-blue-300'
                        : 'border-gray-700 bg-gray-800/50 text-gray-300 hover:border-gray-600'
                    }`}
                  >
                    <div>
                      <p className="text-sm font-medium">{t.template_name}</p>
                      {t.description && (
                        <p className="text-xs text-gray-500 mt-0.5">{t.description}</p>
                      )}
                    </div>
                    {templateId === t.template_id && (
                      <ChevronRight className="w-4 h-4 shrink-0 text-blue-400" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* Aspect ratio */}
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
              Aspect Ratio
            </h2>
            <div className="flex gap-2">
              {ASPECT_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setAspectRatio(opt.value)}
                  className={`flex-1 flex flex-col items-center rounded-lg border px-3 py-3 transition-colors ${
                    aspectRatio === opt.value
                      ? 'border-blue-500 bg-blue-600/10 text-blue-300'
                      : 'border-gray-700 bg-gray-800/50 text-gray-300 hover:border-gray-600'
                  }`}
                >
                  <span className="text-sm font-semibold">{opt.label}</span>
                  <span className="text-xs text-gray-500 mt-0.5">{opt.sub}</span>
                </button>
              ))}
            </div>
          </section>

          {/* Caption preset (optional) */}
          {captionStyles.length > 0 && (
            <section className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
                Captions <span className="text-gray-600 font-normal">(optional)</span>
              </h2>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setCaptionStyleId(null)}
                  className={`rounded-full px-3 py-1 text-xs border transition-colors ${
                    captionStyleId === null
                      ? 'border-blue-500 bg-blue-600/10 text-blue-300'
                      : 'border-gray-700 text-gray-400 hover:border-gray-600'
                  }`}
                >
                  No captions
                </button>
                {captionStyles.map(s => (
                  <button
                    key={s.style_id}
                    onClick={() => setCaptionStyleId(s.style_id)}
                    className={`rounded-full px-3 py-1 text-xs border transition-colors ${
                      captionStyleId === s.style_id
                        ? 'border-blue-500 bg-blue-600/10 text-blue-300'
                        : 'border-gray-700 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    {s.style_name}
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Error banner */}
          {submitError && (
            <div className="rounded-md bg-red-900/30 border border-red-700/50 p-3 text-xs text-red-300">
              {submitError}
            </div>
          )}

          {/* Run button */}
          <Button
            onClick={handleRun}
            disabled={!canSubmit}
            className="w-full py-3 text-base font-semibold"
          >
            {submitting ? <Spinner size="sm" /> : (
              <>
                <Zap className="w-4 h-4 mr-2" />
                Generate
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
