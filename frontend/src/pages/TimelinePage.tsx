import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Video, Eye } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { TimelineEditor } from '../components/Timeline/TimelineEditor'
import { ClipPreviewPanel } from '../components/Timeline/ClipPreviewPanel'
import { TimelinePlayer } from '../components/Timeline/TimelinePlayer'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import { fetchTimeline } from '../api/stories'

export default function TimelinePage() {
  const { timeline_id } = useParams<{ timeline_id: string }>()
  const navigate = useNavigate()
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null)
  const [showPlayer, setShowPlayer] = useState(false)

  const { data: timeline, isLoading, error } = useQuery({
    queryKey: ['timeline', timeline_id],
    queryFn: () => fetchTimeline(timeline_id ?? ''),
    enabled: !!timeline_id,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error || !timeline) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-red-400">
        <p>Failed to load timeline.</p>
        <Button variant="secondary" onClick={() => navigate('/stories')}>
          Go Back
        </Button>
      </div>
    )
  }

  const selectedElement = timeline.elements.find((e) => e.element_id === selectedElementId) ?? null

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-800 bg-gray-950">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-base font-semibold text-gray-100 flex-1">{timeline.timeline_name}</h1>
        <Badge variant="info">{timeline.aspect_ratio}</Badge>
        <Button variant="secondary" onClick={() => setShowPlayer(!showPlayer)}>
          <Eye className="h-4 w-4" />
          Preview
        </Button>
        <Button onClick={() => navigate('/render')}>
          <Video className="h-4 w-4" />
          Render
        </Button>
      </div>

      {/* Player */}
      {showPlayer && (
        <TimelinePlayer
          elements={timeline.elements}
          onClose={() => setShowPlayer(false)}
        />
      )}

      {/* Main content: editor + preview panel */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          <TimelineEditor
            timeline={timeline}
            selectedElementId={selectedElementId}
            onSelectElement={setSelectedElementId}
          />
        </div>
        {/* Preview panel - desktop only */}
        {selectedElementId && (
          <div className="hidden md:block w-80 border-l border-gray-800 bg-gray-950 overflow-y-auto p-4">
            <ClipPreviewPanel element={selectedElement} />
          </div>
        )}
      </div>
    </div>
  )
}
