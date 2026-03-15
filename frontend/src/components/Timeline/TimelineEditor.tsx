import { useState } from 'react'
import { Plus } from 'lucide-react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import { restrictToVerticalAxis } from '@dnd-kit/modifiers'
import { ElementRow } from './ElementRow'
import { TimelineStrip } from './TimelineStrip'
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
  selectedElementId?: string | null
  onSelectElement?: (id: string) => void
}

export function TimelineEditor({ timeline, selectedElementId, onSelectElement }: TimelineEditorProps) {
  const qc = useQueryClient()
  const [elements, setElements] = useState<TimelineElement[]>(timeline.elements)

  const totalDurationMs = elements.reduce((sum, el) => sum + el.duration_ms, 0)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const oldIndex = elements.findIndex((e) => e.element_id === active.id)
    const newIndex = elements.findIndex((e) => e.element_id === over.id)
    if (oldIndex < 0 || newIndex < 0) return

    const newElements = arrayMove(elements, oldIndex, newIndex)
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

      <TimelineStrip
        elements={elements}
        selectedId={selectedElementId ?? null}
        onSelect={(id) => onSelectElement?.(id)}
      />

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        modifiers={[restrictToVerticalAxis]}
        onDragEnd={(e) => void handleDragEnd(e)}
      >
        <SortableContext
          items={elements.map((e) => e.element_id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="flex flex-col gap-2">
            {elements.map((el, i) => (
              <ElementRow
                key={el.element_id}
                element={el}
                index={i}
                total={elements.length}
                selected={el.element_id === selectedElementId}
                onSelect={(id) => onSelectElement?.(id)}
                onDelete={(id) => void handleDelete(id)}
                onUpdate={(id, params) => void handleUpdate(id, params)}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {elements.length === 0 && (
        <div className="flex items-center justify-center h-24 text-gray-500 text-sm">
          No elements. Add clips from the Clips page.
        </div>
      )}
    </div>
  )
}
