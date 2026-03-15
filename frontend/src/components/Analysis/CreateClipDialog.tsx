import { useState, useEffect } from 'react'
import { Dialog } from '../ui/Dialog'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { SpeakerBadge } from '../Transcript/SpeakerBadge'
import { useCreateClip } from '../../hooks/useClips'
import { formatDuration, formatScore } from '../../utils/format'
import type { AnalysisHighlight } from '../../api/types'

interface CreateClipDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  itemId: string
  highlight: AnalysisHighlight | null
}

export function CreateClipDialog({ open, onOpenChange, itemId, highlight }: CreateClipDialogProps) {
  const { mutate: createClip, isPending } = useCreateClip()
  const [clipTitle, setClipTitle] = useState('')
  const [startMs, setStartMs] = useState(0)
  const [endMs, setEndMs] = useState(0)

  useEffect(() => {
    if (highlight) {
      setClipTitle(highlight.segment_text.slice(0, 50))
      setStartMs(highlight.start_ms)
      setEndMs(highlight.end_ms)
    }
  }, [highlight])

  if (!highlight) return null

  const durationMs = endMs - startMs

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    createClip(
      { item_id: itemId, start_ms: startMs, end_ms: endMs, clip_title: clipTitle || undefined },
      { onSuccess: () => onOpenChange(false) },
    )
  }

  function nudge(field: 'start' | 'end', deltaMs: number) {
    if (field === 'start') {
      setStartMs((v) => Math.max(0, v + deltaMs))
    } else {
      setEndMs((v) => Math.max(0, v + deltaMs))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Create Clip from Highlight">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* Read-only highlight info */}
        <div className="flex items-center gap-2 flex-wrap">
          {highlight.speaker_label && <SpeakerBadge speaker={highlight.speaker_label} />}
          <Badge variant="info">{formatScore(highlight.composite_score)}</Badge>
        </div>

        <p className="text-sm text-gray-400 line-clamp-3">{highlight.segment_text}</p>

        {/* Time range with nudge buttons */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-gray-400 mb-1 block">Start</label>
            <div className="flex items-center gap-1">
              <Button type="button" size="sm" variant="ghost" onClick={() => nudge('start', -2000)}>-2s</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => nudge('start', -1000)}>-1s</Button>
              <span className="text-sm text-gray-200 font-mono px-2">{formatDuration(startMs)}</span>
              <Button type="button" size="sm" variant="ghost" onClick={() => nudge('start', 1000)}>+1s</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => nudge('start', 2000)}>+2s</Button>
            </div>
          </div>
          <div>
            <label className="text-sm text-gray-400 mb-1 block">End</label>
            <div className="flex items-center gap-1">
              <Button type="button" size="sm" variant="ghost" onClick={() => nudge('end', -2000)}>-2s</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => nudge('end', -1000)}>-1s</Button>
              <span className="text-sm text-gray-200 font-mono px-2">{formatDuration(endMs)}</span>
              <Button type="button" size="sm" variant="ghost" onClick={() => nudge('end', 1000)}>+1s</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => nudge('end', 2000)}>+2s</Button>
            </div>
          </div>
        </div>

        <p className="text-xs text-gray-500">Duration: {formatDuration(durationMs)}</p>

        <Input
          label="Clip Title"
          value={clipTitle}
          onChange={(e) => setClipTitle(e.target.value)}
          placeholder="Enter clip title..."
        />

        <div className="flex justify-end gap-2 mt-2">
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" loading={isPending} disabled={durationMs <= 0}>
            Create Clip
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
