import { useEffect } from 'react'

type ShortcutMap = Record<string, () => void>

function normalizeKey(e: KeyboardEvent): string {
  const parts: string[] = []
  if (e.ctrlKey || e.metaKey) parts.push('Ctrl')
  if (e.shiftKey) parts.push('Shift')
  if (e.altKey) parts.push('Alt')

  let key = e.key
  if (key === ' ') key = 'Space'

  // Avoid duplicating modifier as key
  if (!['Control', 'Meta', 'Shift', 'Alt'].includes(key)) {
    parts.push(key.length === 1 ? key : key)
  }

  return parts.join('+')
}

function isEditableTarget(e: KeyboardEvent): boolean {
  const el = e.target as HTMLElement
  const tag = el.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  if (el.isContentEditable) return true
  return false
}

export function useGlobalShortcuts(shortcuts: ShortcutMap) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (isEditableTarget(e)) return
      const key = normalizeKey(e)
      const action = shortcuts[key]
      if (action) {
        e.preventDefault()
        action()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [shortcuts])
}
