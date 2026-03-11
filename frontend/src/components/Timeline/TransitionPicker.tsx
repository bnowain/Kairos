import { Select } from '../ui/Select'

interface TransitionPickerProps {
  value: string
  onChange: (value: string) => void
}

const TRANSITIONS = [
  { value: 'cut', label: 'Cut' },
  { value: 'fade', label: 'Fade' },
  { value: 'wipe', label: 'Wipe' },
  { value: 'dissolve', label: 'Dissolve' },
]

export function TransitionPicker({ value, onChange }: TransitionPickerProps) {
  return (
    <Select
      value={value || 'cut'}
      onValueChange={onChange}
      options={TRANSITIONS}
    />
  )
}
