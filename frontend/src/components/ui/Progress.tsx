import { cn } from '../../utils/cn'

interface ProgressProps {
  value: number // 0-100
  className?: string
  barClassName?: string
}

export function Progress({ value, className, barClassName }: ProgressProps) {
  return (
    <div className={cn('h-1.5 w-full rounded-full bg-gray-800 overflow-hidden', className)}>
      <div
        className={cn('h-full rounded-full bg-blue-500 transition-all duration-300', barClassName)}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  )
}
