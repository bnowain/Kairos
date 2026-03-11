import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, BarChart2, Scissors, Loader2 } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Spinner } from '../components/ui/Spinner'
import { Tabs } from '../components/ui/Tabs'
import { SegmentList } from '../components/Transcript/SegmentList'
import { ScorePanel } from '../components/Analysis/ScorePanel'
import { ClipGrid } from '../components/Clips/ClipGrid'
import { useMediaItem } from '../hooks/useLibrary'
import { useSegments, useStartTranscription, useTranscriptionJobs } from '../hooks/useTranscription'
import { useHighlights, useStartAnalysis } from '../hooks/useAnalysis'
import { useClips, useGenerateClips } from '../hooks/useClips'
import { apiUrl } from '../api/client'
import { formatDate, formatDurationSeconds } from '../utils/format'
import { useState } from 'react'
import type { AnalysisHighlight } from '../api/types'

const STATUS_VARIANT: Record<string, 'default' | 'info' | 'warning' | 'success' | 'error'> = {
  queued: 'default',
  downloading: 'info',
  downloaded: 'info',
  ingesting: 'warning',
  ready: 'success',
  error: 'error',
}

export default function ItemPage() {
  const { item_id } = useParams<{ item_id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')

  const { data: item, isLoading: itemLoading } = useMediaItem(item_id ?? '')
  const { data: segments = [], isLoading: segmentsLoading } = useSegments(item_id ?? '')
  const { data: highlights = [], isLoading: highlightsLoading } = useHighlights(item_id ?? '')
  const { data: clipsData, isLoading: clipsLoading } = useClips({ item_id: item_id ?? '' })
  const { data: transcriptionJobs = [] } = useTranscriptionJobs(item_id)

  const { mutate: startTranscription, isPending: transcribing } = useStartTranscription()
  const { mutate: startAnalysis, isPending: analyzing } = useStartAnalysis()
  const { mutate: generateClips, isPending: generatingClips } = useGenerateClips()

  if (itemLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!item) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-500">
        <p>Item not found.</p>
        <Button variant="secondary" onClick={() => navigate('/')}>Go Back</Button>
      </div>
    )
  }

  const activeTranscriptionJob = transcriptionJobs.find(
    (j) => j.job_status === 'running' || j.job_status === 'queued',
  )

  const thumbFilename = item.thumb_path?.split('/').pop()

  function handleCreateClip(_highlight: AnalysisHighlight) {
    // Future: open a dialog to create a clip from this highlight
  }

  const tabs = [
    {
      value: 'overview',
      label: 'Overview',
      content: (
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Thumbnail */}
          <div className="aspect-video rounded-lg bg-gray-800 overflow-hidden">
            {thumbFilename ? (
              <img
                src={apiUrl(`/media/thumbs/${thumbFilename}`)}
                alt={item.item_title ?? 'Thumbnail'}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-600">
                No thumbnail
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wide">Platform</label>
              <p className="text-sm text-gray-200 capitalize">{item.platform}</p>
            </div>
            {item.item_channel && (
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wide">Channel</label>
                <p className="text-sm text-gray-200">{item.item_channel}</p>
              </div>
            )}
            {item.duration_seconds != null && (
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wide">Duration</label>
                <p className="text-sm text-gray-200">{formatDurationSeconds(item.duration_seconds)}</p>
              </div>
            )}
            {item.published_at && (
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wide">Published</label>
                <p className="text-sm text-gray-200">{formatDate(item.published_at)}</p>
              </div>
            )}
            {item.original_url && (
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wide">URL</label>
                <a
                  href={item.original_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-400 hover:text-blue-300 truncate block"
                >
                  {item.original_url}
                </a>
              </div>
            )}
            {item.item_description && (
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wide">Description</label>
                <p className="text-sm text-gray-400 line-clamp-4">{item.item_description}</p>
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      value: 'transcript',
      label: (
        <span className="flex items-center gap-1.5">
          <FileText className="h-3.5 w-3.5" />
          Transcript
          {segments.length > 0 && (
            <span className="text-xs bg-gray-700 px-1.5 py-0.5 rounded">{segments.length}</span>
          )}
        </span>
      ),
      content: (
        <div className="flex flex-col h-full">
          {activeTranscriptionJob && (
            <div className="flex items-center gap-2 px-4 py-2 bg-blue-900/20 border-b border-blue-900/30 text-sm text-blue-300">
              <Loader2 className="h-4 w-4 animate-spin" />
              Transcription {activeTranscriptionJob.job_status}...
            </div>
          )}
          <div className="flex-1 overflow-hidden">
            <SegmentList
              segments={segments}
              isLoading={segmentsLoading}
              itemId={item_id ?? ''}
            />
          </div>
        </div>
      ),
    },
    {
      value: 'analysis',
      label: (
        <span className="flex items-center gap-1.5">
          <BarChart2 className="h-3.5 w-3.5" />
          Analysis
        </span>
      ),
      content: (
        <div className="flex-1 overflow-y-auto">
          <ScorePanel
            highlights={highlights}
            isLoading={highlightsLoading}
            onCreateClip={handleCreateClip}
          />
        </div>
      ),
    },
    {
      value: 'clips',
      label: (
        <span className="flex items-center gap-1.5">
          <Scissors className="h-3.5 w-3.5" />
          Clips
          {(clipsData?.total ?? 0) > 0 && (
            <span className="text-xs bg-gray-700 px-1.5 py-0.5 rounded">{clipsData?.total}</span>
          )}
        </span>
      ),
      content: (
        <div className="p-6">
          <ClipGrid
            clips={clipsData?.items ?? []}
            isLoading={clipsLoading}
            emptyMessage="No clips yet. Run analysis and then Generate Clips."
          />
        </div>
      ),
    },
  ]

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-start gap-3 px-6 py-4 border-b border-gray-800 bg-gray-950">
        <Button variant="ghost" size="sm" aria-label="Back to library" onClick={() => navigate('/')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-base font-semibold text-gray-100 truncate">
              {item.item_title ?? 'Untitled'}
            </h1>
            <Badge variant={STATUS_VARIANT[item.item_status] ?? 'default'}>
              {item.item_status}
            </Badge>
          </div>
          {item.item_channel && (
            <p className="text-sm text-gray-500 mt-0.5">{item.item_channel}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          <Button
            size="sm"
            variant="secondary"
            loading={transcribing}
            disabled={segments.length > 0 || !!activeTranscriptionJob}
            onClick={() =>
              startTranscription({ itemId: item_id ?? '', opts: { diarize: true } })
            }
          >
            Transcribe
          </Button>
          <Button
            size="sm"
            variant="secondary"
            loading={analyzing}
            disabled={segments.length === 0}
            onClick={() => startAnalysis(item_id ?? '')}
          >
            Analyze
          </Button>
          <Button
            size="sm"
            loading={generatingClips}
            disabled={highlights.length === 0}
            onClick={() => generateClips(item_id ?? '')}
          >
            <Scissors className="h-3.5 w-3.5" />
            Generate Clips
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex-1 overflow-hidden">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          tabs={tabs}
          className="h-full"
        />
      </div>
    </div>
  )
}
