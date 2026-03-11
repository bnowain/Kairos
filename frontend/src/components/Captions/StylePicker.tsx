import { PresetCard } from './PresetCard'
import { Spinner } from '../ui/Spinner'
import type { CaptionStyle } from '../../api/types'

interface StylePickerProps {
  styles: CaptionStyle[]
  isLoading: boolean
  selectedId: string | null
  onSelect: (styleId: string) => void
}

export function StylePicker({ styles, isLoading, selectedId, onSelect }: StylePickerProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-20">
        <Spinner />
      </div>
    )
  }

  if (styles.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-4 text-center">
        No caption styles configured.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-2">
      {styles.map((s) => (
        <PresetCard
          key={s.style_id}
          style={s}
          selected={selectedId === s.style_id}
          onClick={() => onSelect(s.style_id)}
        />
      ))}
    </div>
  )
}
