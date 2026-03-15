import { create } from 'zustand'

export interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'info'
  createdAt: number
}

interface ToastStore {
  toasts: Toast[]
  addToast: (message: string, type: Toast['type']) => void
  removeToast: (id: string) => void
}

const timeouts = new Map<string, ReturnType<typeof setTimeout>>()

export const useToastStore = create<ToastStore>((set, get) => ({
  toasts: [],
  addToast: (message, type) => {
    const id = crypto.randomUUID()
    const toast: Toast = { id, message, type, createdAt: Date.now() }
    set((s) => ({ toasts: [...s.toasts, toast] }))
    if (type !== 'error') {
      const timeout = setTimeout(() => {
        get().removeToast(id)
      }, 4000)
      timeouts.set(id, timeout)
    }
  },
  removeToast: (id) => {
    const timeout = timeouts.get(id)
    if (timeout) {
      clearTimeout(timeout)
      timeouts.delete(id)
    }
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
  },
}))

export const toast = {
  success: (msg: string) => useToastStore.getState().addToast(msg, 'success'),
  error: (msg: string) => useToastStore.getState().addToast(msg, 'error'),
  info: (msg: string) => useToastStore.getState().addToast(msg, 'info'),
}
