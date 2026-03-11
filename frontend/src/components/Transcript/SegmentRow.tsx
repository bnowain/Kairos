import { SpeakerBadge } from './SpeakerBadge'
import { formatMs } from '../../utils/format'
import type { TranscriptionSegment } from '../../api/types'

interface SegmentRowProps {
  segment: TranscriptionSegment
}

export function SegmentRow({ segment }: SegmentRowProps) {
  return (
    <div className="flex gap-3 py-2.5 px-4 hover:bg-gray-800/50 transition-colors border-b border-gray-800/50">
      <div className="flex flex-col items-end gap-1 shrink-0 w-20 pt-0.5">
        <span className="text-xs font-mono text-gray-500">{formatMs(segment.start_ms)}</span>
        <span className="text-xs font-mono text-gray-600">{formatMs(segment.end_ms)}</span>
      </div>
      <div className="flex-1 flex flex-col gap-1">
        <SpeakerBadge speaker={segment.speaker_label} />
        <p className="text-sm text-gray-200 leading-relaxed">{segment.segment_text}</p>
      </div>
    </div>
  )
}
