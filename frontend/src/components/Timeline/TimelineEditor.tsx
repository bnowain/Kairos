import { useState } from 'react'
import { Plus } from 'lucide-react'
import { ElementRow } from './ElementRow'
import { Button } from '../ui/Button'
import { formatDuration } from '../../utils/format'
import {
  updateTimelineElement,
  reorderElements,
  addTitleCard,
  deleteElement,
} from '../../api/stories'
import { useQueryClient } from '@tanstack/react-query'
import type { Timeline, TimelineElement } from '../../api/types'

interface TimelineEditorProps {
  timeline: Timeline
}

export function TimelineEditor({ timeline }: TimelineEditorProps) {
  const qc = useQueryClient()
  const [elements, setElements] = useState<TimelineElement[]>(timeline.elements)

  const totalDurationMs = elements.reduce((sum, el) => sum + el.duration_ms, 0)

  async function moveElement(elementId: string, direction: 'up' | 'down') {
    const idx = elements.findIndex((e) => e.element_id === elementId)
    if (idx < 0) return
    const newElements = [...elements]
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1
    if (swapIdx < 0 || swapIdx >= newElements.length) return
    const temp = newElements[idx]!
    newElements[idx] = newElements[swapIdx]!
    newElements[swapIdx] = temp
    setElements(newElements)
    await reorderElements(
      timeline.timeline_id,
      newElements.map((e) => e.element_id),
    )
    void qc.invalidateQueries({ queryKey: ['timeline', timeline.timeline_id] })
  }

  async function handleDelete(elementId: string) {
    await deleteElement(timeline.timeline_id, elementId)
    setElements((prev) => prev.filter((e) => e.element_id !== elementId))
    void qc.invalidateQueries({ queryKey: ['timeline', timeline.timeline_id] })
  }

  async function handleUpdate(elementId: string, params: Partial<TimelineElement>) {
    await updateTimelineElement(timeline.timeline_id, elementId, params)
    setElements((prev) =>
      prev.map((e) => (e.element_id === elementId ? { ...e, ...params } : e)),
    )
  }

  async function handleAddTitleCard() {
    const el = await addTitleCard(timeline.timeline_id, '')
    setElements((prev) => [...prev, el])
    void qc.invalidateQueries({ queryKey: ['timeline', timeline.timeline_id] })
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-400">
          {elements.length} elements · Total: {formatDuration(totalDurationMs)}
        </div>
        <Button size="sm" variant="secondary" onClick={() => void handleAddTitleCard()}>
          <Plus className="h-4 w-4" />
          Add Title Card
        </Button>
      </div>

      <div className="flex flex-col gap-2">
        {elements.map((el, i) => (
          <ElementRow
            key={el.element_id}
            element={el}
            index={i}
            total={elements.length}
            onMoveUp={(id) => void moveElement(id, 'up')}
            onMoveDown={(id) => void moveElement(id, 'down')}
            onDelete={(id) => void handleDelete(id)}
            onUpdate={(id, params) => void handleUpdate(id, params)}
          />
        ))}
      </div>

      {elements.length === 0 && (
        <div className="flex items-center justify-center h-24 text-gray-500 text-sm">
          No elements. Add clips from the Clips page.
        </div>
      )}
    </div>
  )
}
