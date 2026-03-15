import { Dialog } from '../ui/Dialog'
import { useAppStore } from '../../store/useAppStore'

const SECTIONS = [
  {
    title: 'Global',
    shortcuts: [
      { keys: '?', description: 'Toggle this help dialog' },
      { keys: '/', description: 'Focus search / first text input' },
    ],
  },
  {
    title: 'Video Player',
    shortcuts: [
      { keys: 'Space', description: 'Play / Pause' },
      { keys: 'ArrowLeft', description: 'Seek back 5s' },
      { keys: 'ArrowRight', description: 'Seek forward 5s' },
      { keys: 'Shift + ArrowLeft', description: 'Seek back 1s' },
      { keys: 'Shift + ArrowRight', description: 'Seek forward 1s' },
    ],
  },
  {
    title: 'Clips Page',
    shortcuts: [
      { keys: 'Ctrl + A', description: 'Select all clips' },
      { keys: 'Escape', description: 'Clear selection' },
      { keys: 'Delete', description: 'Delete selected clips' },
    ],
  },
]

export function ShortcutHelpDialog() {
  const open = useAppStore((s) => s.shortcutHelpOpen)
  const setOpen = useAppStore((s) => s.setShortcutHelpOpen)

  return (
    <Dialog open={open} onOpenChange={setOpen} title="Keyboard Shortcuts">
      <div className="flex flex-col gap-5">
        {SECTIONS.map((section) => (
          <div key={section.title}>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              {section.title}
            </h3>
            <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
              {section.shortcuts.map((s) => (
                <div key={s.keys} className="contents">
                  <kbd className="text-xs font-mono bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-300 text-right whitespace-nowrap">
                    {s.keys}
                  </kbd>
                  <span className="text-sm text-gray-400">{s.description}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Dialog>
  )
}
