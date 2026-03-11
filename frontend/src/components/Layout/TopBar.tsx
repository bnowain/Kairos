import type { ReactNode } from 'react'

interface TopBarProps {
  title: ReactNode
  actions?: ReactNode
}

export function TopBar({ title, actions }: TopBarProps) {
  return (
    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-950">
      <h1 className="text-lg font-semibold text-gray-100">{title}</h1>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
