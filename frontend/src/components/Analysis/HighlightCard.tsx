import { Scissors } from 'lucide-react'
import { Button } from '../ui/Button'
import { ScoreBar } from './ScoreBar'
import { SpeakerBadge } from '../Transcript/SpeakerBadge'
import { formatDuration, formatScore } from '../../utils/format'
import type { AnalysisHighlight } from '../../api/types'

interface HighlightCardProps {
  highlight: AnalysisHighlight
  rank: number
  onCreateClip?: (highlight: AnalysisHighlight) => void
}

export function HighlightCard({ highlight, rank, onCreateClip }: HighlightCardProps) {
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-4 flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-600/20 text-blue-400 text-xs font-bold">
          {rank}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {highlight.speaker_label && (
              <SpeakerBadge speaker={highlight.speaker_label} />
            )}
            <span className="text-xs text-gray-500 font-mono">
              {formatDuration(highlight.start_ms)} – {formatDuration(highlight.end_ms)}
            </span>
            <span className="ml-auto text-sm font-semibold text-green-400">
              {formatScore(highlight.composite_score)}
            </span>
          </div>
          <p className="text-sm text-gray-300 leading-relaxed line-clamp-3">
            {highlight.segment_text}
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-1.5 px-10">
        {Object.entries(highlight.scores).map(([signal, score]) => (
          <ScoreBar key={signal} label={signal} value={score} />
        ))}
      </div>

      {onCreateClip && (
        <div className="flex justify-end">
          <Button size="sm" variant="secondary" onClick={() => onCreateClip(highlight)}>
            <Scissors className="h-3.5 w-3.5" />
            Create Clip
          </Button>
        </div>
      )}
    </div>
  )
}
