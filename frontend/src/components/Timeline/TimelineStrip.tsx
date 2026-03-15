import * as Tooltip from '@radix-ui/react-tooltip'
import { cn } from '../../utils/cn'
import { formatDuration } from '../../utils/format'
import type { TimelineElement } from '../../api/types'

interface TimelineStripProps {
  elements: TimelineElement[]
  selectedId: string | null
  onSelect: (id: string) => void
}

const typeColors: Record<string, string> = {
  clip: 'bg-blue-500',
  transition: 'bg-gray-600',
  title_card: 'bg-yellow-500',
  overlay: 'bg-purple-500',
}

export function TimelineStrip({ elements, selectedId, onSelect }: TimelineStripProps) {
  const totalDurationMs = elements.reduce((sum, el) => sum + el.duration_ms, 0)
  if (totalDurationMs === 0) return null

  return (
    <Tooltip.Provider delayDuration={200}>
      <div className="flex items-stretch h-10 rounded-lg overflow-hidden border border-gray-700 overflow-x-auto">
        {elements.map((el) => {
          const widthPct = (el.duration_ms / totalDurationMs) * 100
          const isTransition = el.element_type === 'transition'
          const isSelected = el.element_id === selectedId

          return (
            <Tooltip.Root key={el.element_id}>
              <Tooltip.Trigger asChild>
                <button
                  className={cn(
                    typeColors[el.element_type] ?? 'bg-gray-500',
                    'transition-all hover:brightness-110 cursor-pointer border-r border-gray-900/40 last:border-r-0',
                    isSelected && 'ring-2 ring-white ring-inset',
                  )}
                  style={{
                    width: `${widthPct}%`,
                    minWidth: isTransition ? '4px' : '24px',
                  }}
                  onClick={() => onSelect(el.element_id)}
                />
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content
                  side="top"
                  sideOffset={6}
                  className="rounded-md bg-gray-800 border border-gray-700 px-2.5 py-1.5 text-xs text-gray-200 shadow-lg z-50"
                >
                  <span className="capitalize">{el.element_type}</span>
                  {' · '}
                  {formatDuration(el.duration_ms)}
                  <Tooltip.Arrow className="fill-gray-800" />
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          )
        })}
      </div>
    </Tooltip.Provider>
  )
}
