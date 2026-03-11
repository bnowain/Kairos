import { useNavigate } from 'react-router-dom'
import { Edit, Video, Film } from 'lucide-react'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { formatDuration } from '../../utils/format'
import type { Timeline } from '../../api/types'

interface TimelinePreviewProps {
  timeline: Timeline
}

export function TimelinePreview({ timeline }: TimelinePreviewProps) {
  const navigate = useNavigate()

  const totalDurationMs = timeline.elements.reduce((sum, el) => sum + el.duration_ms, 0)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-100">{timeline.timeline_name}</h3>
          <p className="text-sm text-gray-400">
            {timeline.element_count} elements · {formatDuration(totalDurationMs)} total
          </p>
        </div>
        <Badge variant="info">{timeline.aspect_ratio}</Badge>
      </div>

      <div className="flex flex-col gap-1.5">
        {timeline.elements.map((el, i) => (
          <div
            key={el.element_id}
            className="flex items-center gap-3 rounded-md bg-gray-800 px-3 py-2"
          >
            <span className="text-xs text-gray-600 w-5 text-right shrink-0">{i + 1}</span>
            {el.element_type === 'clip' ? (
              <Film className="h-4 w-4 text-blue-400 shrink-0" />
            ) : el.element_type === 'transition' ? (
              <span className="text-blue-400 text-sm">→</span>
            ) : (
              <span className="text-yellow-400 text-sm">T</span>
            )}
            <span className="flex-1 text-sm text-gray-300 capitalize">{el.element_type}</span>
            <span className="text-xs text-gray-500 font-mono">{formatDuration(el.duration_ms)}</span>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <Button
          variant="secondary"
          className="flex-1"
          onClick={() => navigate(`/timeline/${timeline.timeline_id}`)}
        >
          <Edit className="h-4 w-4" />
          Edit Timeline
        </Button>
        <Button
          className="flex-1"
          onClick={() => navigate('/render')}
        >
          <Video className="h-4 w-4" />
          Render
        </Button>
      </div>
    </div>
  )
}
