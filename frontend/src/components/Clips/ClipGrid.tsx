import { Scissors } from 'lucide-react'
import { ClipCard } from './ClipCard'
import { ClipCardSkeleton } from './ClipCardSkeleton'
import { EmptyState } from '../ui/EmptyState'
import type { Clip } from '../../api/types'

interface ClipGridProps {
  clips: Clip[]
  isLoading: boolean
  error?: Error | null
  emptyMessage?: string
  selectable?: boolean
  selectedIds?: Set<string>
  onToggleSelect?: (clipId: string) => void
}

export function ClipGrid({ clips, isLoading, error, emptyMessage, selectable, selectedIds, onToggleSelect }: ClipGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {Array.from({ length: 10 }).map((_, i) => (
          <ClipCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-red-400">
        <p className="font-medium">Failed to load clips</p>
        <p className="text-sm text-gray-500">{error.message}</p>
      </div>
    )
  }

  if (clips.length === 0) {
    return (
      <EmptyState
        icon={Scissors}
        heading="No clips yet"
        description={emptyMessage ?? 'No clips yet.'}
      />
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {clips.map((clip) => (
        <ClipCard
          key={clip.clip_id}
          clip={clip}
          selectable={selectable}
          selected={selectedIds?.has(clip.clip_id)}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  )
}
