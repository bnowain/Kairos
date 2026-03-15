import { X } from 'lucide-react'
import { useToastStore } from '../../store/useToastStore'

const BORDER_COLORS = {
  success: 'border-l-green-500',
  error: 'border-l-red-500',
  info: 'border-l-blue-500',
} as const

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)
  const removeToast = useToastStore((s) => s.removeToast)

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-start gap-3 rounded-lg bg-gray-900 border border-gray-700 border-l-4 ${BORDER_COLORS[t.type]} p-3 shadow-lg animate-slideIn`}
        >
          <p className="flex-1 text-sm text-gray-200">{t.message}</p>
          <button
            onClick={() => removeToast(t.id)}
            className="shrink-0 text-gray-500 hover:text-gray-300"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
