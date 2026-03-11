import { cn } from '../../utils/cn'
import type { HTMLAttributes } from 'react'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'secondary'
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const variants = {
    default: 'bg-gray-700 text-gray-300',
    success: 'bg-green-900 text-green-300',
    warning: 'bg-yellow-900 text-yellow-300',
    error: 'bg-red-900 text-red-300',
    info: 'bg-blue-900 text-blue-300',
    secondary: 'bg-gray-800 text-gray-400',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium',
        variants[variant],
        className,
      )}
      {...props}
    />
  )
}
