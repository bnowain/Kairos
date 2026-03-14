import { useRef, useEffect, useState, useCallback } from 'react'
import { Download } from 'lucide-react'
import { SpeakerBadge } from '../Transcript/SpeakerBadge'
import { Button } from '../ui/Button'
import { formatMs } from '../../utils/format'
import { exportTranscript } from '../../api/transcription'
import type { TranscriptionSegment } from '../../api/types'

interface TranscriptPanelProps {
  segments: TranscriptionSegment[]
  activeSegmentIndex: number
  clipInMs: number | null
  clipOutMs: number | null
  itemId: string
  onSegmentClick: (segment: TranscriptionSegment) => void
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function isInClipRange(seg: TranscriptionSegment, inMs: number | null, outMs: number | null): boolean {
  if (inMs == null || outMs == null) return false
  return seg.start_ms < outMs && seg.end_ms > inMs
}

export function TranscriptPanel({
  segments,
  activeSegmentIndex,
  clipInMs,
  clipOutMs,
  itemId,
  onSegmentClick,
}: TranscriptPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const segmentRefs = useRef<(HTMLDivElement | null)[]>([])
  const [autoFollow, setAutoFollow] = useState(true)
  const userScrolledRef = useRef(false)

  // Auto-scroll to active segment
  useEffect(() => {
    if (!autoFollow || activeSegmentIndex < 0) return
    const el = segmentRefs.current[activeSegmentIndex]
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [activeSegmentIndex, autoFollow])

  // Detect manual scroll → disable auto-follow
  const handleScroll = useCallback(() => {
    userScrolledRef.current = true
    setAutoFollow(false)
  }, [])

  const handleSegmentClick = useCallback(
    (seg: TranscriptionSegment) => {
      setAutoFollow(true)
      userScrolledRef.current = false
      onSegmentClick(seg)
    },
    [onSegmentClick],
  )

  async function handleExport(format: 'srt' | 'vtt' | 'json') {
    const blob = await exportTranscript(itemId, format)
    downloadBlob(blob, `transcript.${format}`)
  }

  if (segments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500">
        <p>No transcript available.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 shrink-0">
        <span className="text-xs text-gray-400">{segments.length} segments</span>
        <button
          onClick={() => { setAutoFollow(true); userScrolledRef.current = false }}
          className={`ml-1 text-xs px-2 py-0.5 rounded transition-colors ${
            autoFollow
              ? 'bg-blue-600/20 text-blue-400'
              : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Follow
        </button>
        <div className="flex-1" />
        <Button variant="ghost" size="sm" onClick={() => void handleExport('srt')}>
          <Download className="h-3 w-3" /> SRT
        </Button>
        <Button variant="ghost" size="sm" onClick={() => void handleExport('vtt')}>
          <Download className="h-3 w-3" /> VTT
        </Button>
        <Button variant="ghost" size="sm" onClick={() => void handleExport('json')}>
          <Download className="h-3 w-3" /> JSON
        </Button>
      </div>

      {/* Segments list */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto"
      >
        {segments.map((seg, i) => {
          const isActive = i === activeSegmentIndex
          const inRange = isInClipRange(seg, clipInMs, clipOutMs)
          return (
            <div
              key={seg.segment_id}
              ref={(el) => { segmentRefs.current[i] = el }}
              onClick={() => handleSegmentClick(seg)}
              className={`flex gap-3 py-2 px-3 cursor-pointer transition-colors border-l-2 ${
                isActive
                  ? 'bg-blue-900/20 border-l-blue-500'
                  : inRange
                    ? 'bg-teal-900/10 border-l-teal-500/50'
                    : 'border-l-transparent hover:bg-gray-800/50'
              }`}
            >
              <button
                onClick={(e) => { e.stopPropagation(); handleSegmentClick(seg) }}
                className="text-xs font-mono text-gray-500 hover:text-blue-400 shrink-0 w-16 text-right pt-0.5 transition-colors"
              >
                {formatMs(seg.start_ms)}
              </button>
              <div className="flex-1 flex flex-col gap-0.5 min-w-0">
                <SpeakerBadge speaker={seg.speaker_label} />
                <p className="text-sm text-gray-200 leading-relaxed">{seg.segment_text}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
