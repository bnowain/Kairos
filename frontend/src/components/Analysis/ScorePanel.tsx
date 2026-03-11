import { HighlightCard } from './HighlightCard'
import { Spinner } from '../ui/Spinner'
import type { AnalysisHighlight } from '../../api/types'

interface ScorePanelProps {
  highlights: AnalysisHighlight[]
  isLoading: boolean
  onCreateClip?: (highlight: AnalysisHighlight) => void
}

export function ScorePanel({ highlights, isLoading, onCreateClip }: ScorePanelProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Spinner />
      </div>
    )
  }

  if (highlights.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-gray-500">
        <p>No analysis yet. Run analysis to score segments.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      {highlights.map((h, i) => (
        <HighlightCard
          key={h.segment_id}
          highlight={h}
          rank={i + 1}
          onCreateClip={onCreateClip}
        />
      ))}
    </div>
  )
}
