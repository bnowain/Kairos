import { create } from 'zustand'

interface AppStore {
  selectedItemId: string | null
  setSelectedItemId: (id: string | null) => void

  activeItemTab: 'overview' | 'transcript' | 'analysis' | 'clips'
  setActiveItemTab: (tab: 'overview' | 'transcript' | 'analysis' | 'clips') => void

  downloadDialogOpen: boolean
  setDownloadDialogOpen: (open: boolean) => void

  renderDialogOpen: boolean
  setRenderDialogOpen: (open: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  selectedItemId: null,
  setSelectedItemId: (id) => set({ selectedItemId: id }),

  activeItemTab: 'overview',
  setActiveItemTab: (tab) => set({ activeItemTab: tab }),

  downloadDialogOpen: false,
  setDownloadDialogOpen: (open) => set({ downloadDialogOpen: open }),

  renderDialogOpen: false,
  setRenderDialogOpen: (open) => set({ renderDialogOpen: open }),
}))
