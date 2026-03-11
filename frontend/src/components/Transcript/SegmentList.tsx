import { Download } from 'lucide-react'
import { SegmentRow } from './SegmentRow'
import { Spinner } from '../ui/Spinner'
import { Button } from '../ui/Button'
import { exportTranscript } from '../../api/transcription'
import type { TranscriptionSegment } from '../../api/types'

interface SegmentListProps {
  segments: TranscriptionSegment[]
  isLoading: boolean
  itemId: string
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function SegmentList({ segments, isLoading, itemId }: SegmentListProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Spinner />
      </div>
    )
  }

  if (segments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-gray-500">
        <p>No transcript yet. Run transcription to generate segments.</p>
      </div>
    )
  }

  async function handleExport(format: 'srt' | 'vtt' | 'json') {
    const blob = await exportTranscript(itemId, format)
    downloadBlob(blob, `transcript.${format}`)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
        <span className="text-sm text-gray-400">{segments.length} segments</span>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void handleExport('srt')}
        >
          <Download className="h-3.5 w-3.5" />
          SRT
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void handleExport('vtt')}
        >
          <Download className="h-3.5 w-3.5" />
          VTT
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void handleExport('json')}
        >
          <Download className="h-3.5 w-3.5" />
          JSON
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {segments.map((seg) => (
          <SegmentRow key={seg.segment_id} segment={seg} />
        ))}
      </div>
    </div>
  )
}
