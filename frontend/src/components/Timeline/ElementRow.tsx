import { Film, Trash2, GripVertical } from 'lucide-react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Button } from '../ui/Button'
import { TransitionPicker } from './TransitionPicker'
import { Input } from '../ui/Input'
import { formatDuration } from '../../utils/format'
import { cn } from '../../utils/cn'
import type { TimelineElement } from '../../api/types'

interface ElementRowProps {
  element: TimelineElement
  index: number
  total: number
  selected?: boolean
  onSelect?: (elementId: string) => void
  onDelete: (elementId: string) => void
  onUpdate: (elementId: string, params: Partial<TimelineElement>) => void
}

export function ElementRow({
  element,
  index,
  selected,
  onSelect,
  onDelete,
  onUpdate,
}: ElementRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: element.element_id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const params = element.element_params
    ? (JSON.parse(element.element_params) as Record<string, string>)
    : {}

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-3 rounded-lg bg-gray-900 border px-3 py-2.5',
        selected ? 'border-blue-500' : 'border-gray-800',
        isDragging && 'opacity-50 z-10',
      )}
      onClick={() => onSelect?.(element.element_id)}
    >
      {/* Drag handle */}
      <button
        className="shrink-0 cursor-grab active:cursor-grabbing text-gray-600 hover:text-gray-400 touch-none"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4" />
      </button>

      <span className="text-xs text-gray-600 w-6 text-center shrink-0">{index + 1}</span>

      {/* Type icon */}
      <div className="shrink-0">
        {element.element_type === 'clip' && <Film className="h-4 w-4 text-blue-400" />}
        {element.element_type === 'transition' && (
          <span className="text-blue-400 font-bold">→</span>
        )}
        {element.element_type === 'title_card' && (
          <span className="text-yellow-400 font-bold text-sm">T</span>
        )}
        {element.element_type === 'overlay' && (
          <span className="text-purple-400 font-bold text-sm">O</span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {element.element_type === 'transition' ? (
          <div className="w-40">
            <TransitionPicker
              value={params.transition_type ?? 'cut'}
              onChange={(v) =>
                onUpdate(element.element_id, {
                  element_params: JSON.stringify({ ...params, transition_type: v }),
                })
              }
            />
          </div>
        ) : element.element_type === 'title_card' ? (
          <Input
            placeholder="Title card text..."
            defaultValue={params.text ?? ''}
            onBlur={(e) =>
              onUpdate(element.element_id, {
                element_params: JSON.stringify({ ...params, text: e.target.value }),
              })
            }
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="text-sm text-gray-300 capitalize">
            {element.element_type} {element.clip_id ? `(${element.clip_id.slice(0, 8)}…)` : ''}
          </span>
        )}
      </div>

      <span className="text-xs text-gray-500 font-mono shrink-0 w-14 text-right">
        {formatDuration(element.duration_ms)}
      </span>

      <Button
        variant="ghost"
        size="sm"
        className="shrink-0 text-red-500 hover:text-red-400 hover:bg-red-900/20"
        onClick={(e) => {
          e.stopPropagation()
          onDelete(element.element_id)
        }}
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  )
}
