import * as RadixSelect from '@radix-ui/react-select'
import { ChevronDown, Check } from 'lucide-react'
import { cn } from '../../utils/cn'

interface SelectOption {
  value: string
  label: string
}

interface SelectProps {
  value: string
  onValueChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  className?: string
  label?: string
}

// Radix UI Select.Item rejects empty string values — use a sentinel internally
const EMPTY_VALUE = '__empty__'

function toInternal(v: string) { return v === '' ? EMPTY_VALUE : v }
function toExternal(v: string) { return v === EMPTY_VALUE ? '' : v }

export function Select({
  value,
  onValueChange,
  options,
  placeholder = 'Select...',
  disabled,
  className,
  label,
}: SelectProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm text-gray-400">{label}</label>}
      <RadixSelect.Root
        value={toInternal(value)}
        onValueChange={(v) => onValueChange(toExternal(v))}
        disabled={disabled}
      >
        <RadixSelect.Trigger
          className={cn(
            'flex h-9 w-full items-center justify-between rounded-md border border-gray-700 bg-gray-800 px-3 text-sm text-gray-100 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50',
            className,
          )}
        >
          <RadixSelect.Value placeholder={placeholder} />
          <RadixSelect.Icon>
            <ChevronDown className="h-4 w-4 text-gray-500" />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>
        <RadixSelect.Portal>
          <RadixSelect.Content className="z-50 min-w-[8rem] rounded-md border border-gray-700 bg-gray-800 shadow-xl">
            <RadixSelect.Viewport className="p-1">
              {options.map((opt) => (
                <RadixSelect.Item
                  key={toInternal(opt.value)}
                  value={toInternal(opt.value)}
                  className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm text-gray-200 outline-none hover:bg-gray-700 data-[highlighted]:bg-gray-700 data-[state=checked]:text-blue-400"
                >
                  <RadixSelect.ItemIndicator>
                    <Check className="h-4 w-4" />
                  </RadixSelect.ItemIndicator>
                  <RadixSelect.ItemText>{opt.label}</RadixSelect.ItemText>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
    </div>
  )
}
