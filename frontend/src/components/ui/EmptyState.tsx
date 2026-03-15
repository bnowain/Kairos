import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: LucideIcon
  heading: string
  description: string
  action?: ReactNode
}

export function EmptyState({ icon: Icon, heading, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <Icon className="h-12 w-12 text-gray-600" />
      <h3 className="text-lg font-medium text-gray-400">{heading}</h3>
      <p className="text-sm text-gray-500 text-center max-w-xs">{description}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
