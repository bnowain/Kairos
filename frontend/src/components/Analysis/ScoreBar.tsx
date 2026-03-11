import { cn } from '../../utils/cn'

interface ScoreBarProps {
  label: string
  value: number // 0-1
  className?: string
}

const signalColors: Record<string, string> = {
  virality: 'bg-blue-500',
  emotional: 'bg-purple-500',
  controversy: 'bg-red-500',
  hook: 'bg-orange-500',
  composite: 'bg-green-500',
}

export function ScoreBar({ label, value, className }: ScoreBarProps) {
  const color = signalColors[label.toLowerCase()] ?? 'bg-gray-500'
  const pct = Math.round(value * 100)

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="text-xs text-gray-500 w-20 shrink-0 capitalize">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-gray-800 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-400 w-8 text-right">{pct}%</span>
    </div>
  )
}
