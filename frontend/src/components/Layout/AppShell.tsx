import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { BottomNav } from './BottomNav'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-gray-950 md:flex-row">
      {/* Desktop sidebar — hidden on mobile */}
      <Sidebar />
      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden min-h-0">
        {children}
      </main>
      {/* Mobile bottom nav — hidden on desktop (md:hidden in BottomNav itself) */}
      <BottomNav />
    </div>
  )
}
