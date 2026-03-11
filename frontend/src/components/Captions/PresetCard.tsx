import { cn } from '../../utils/cn'
import type { CaptionStyle } from '../../api/types'

interface PresetCardProps {
  style: CaptionStyle
  selected?: boolean
  onClick?: () => void
}

export function PresetCard({ style, selected, onClick }: PresetCardProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'text-left rounded-lg border p-3 transition-colors',
        selected ? 'border-blue-500 bg-blue-600/10' : 'border-gray-800 bg-gray-900 hover:border-gray-700',
      )}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-gray-100">{style.style_name}</span>
        {style.platform_preset && (
          <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
            {style.platform_preset}
          </span>
        )}
      </div>
      <div className="text-xs text-gray-500">
        {style.font_name} {style.font_size}px · {style.position}
      </div>
    </button>
  )
}
