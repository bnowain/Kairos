import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { BottomNav } from './BottomNav'
import { ToastContainer } from '../ui/Toast'
import { ShortcutHelpDialog } from './ShortcutHelpDialog'
import { useGlobalShortcuts } from '../../hooks/useKeyboardShortcuts'
import { useAppStore } from '../../store/useAppStore'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const setShortcutHelpOpen = useAppStore((s) => s.setShortcutHelpOpen)
  const shortcutHelpOpen = useAppStore((s) => s.shortcutHelpOpen)

  const shortcuts = useMemo(
    () => ({
      '?': () => setShortcutHelpOpen(!shortcutHelpOpen),
      '/': () => {
        const input = document.querySelector<HTMLInputElement>('input[type="text"], input:not([type])')
        input?.focus()
      },
    }),
    [setShortcutHelpOpen, shortcutHelpOpen],
  )

  useGlobalShortcuts(shortcuts)

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
      <ToastContainer />
      <ShortcutHelpDialog />
    </div>
  )
}
