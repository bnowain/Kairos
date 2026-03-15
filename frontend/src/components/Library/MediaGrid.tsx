import { RefreshCw, Film } from 'lucide-react'
import { MediaCard } from './MediaCard'
import { MediaCardSkeleton } from './MediaCardSkeleton'
import { EmptyState } from '../ui/EmptyState'
import type { MediaItem } from '../../api/types'
import type { ReactNode } from 'react'

interface MediaGridProps {
  items: MediaItem[]
  isLoading: boolean
  error?: Error | null
  onRefresh?: () => void
  emptyAction?: ReactNode
}

export function MediaGrid({ items, isLoading, error, onRefresh, emptyAction }: MediaGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 p-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <MediaCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-2 text-red-400">
        <p className="font-medium">Failed to load library</p>
        <p className="text-sm text-gray-500">{error.message}</p>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <EmptyState
        icon={Film}
        heading="Your library is empty"
        description="Upload or download videos to get started"
        action={emptyAction}
      />
    )
  }

  return (
    <div>
      {/* Pull-to-refresh on mobile */}
      {onRefresh && (
        <div className="flex justify-center pt-3 pb-1 sm:hidden">
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 text-xs text-gray-500 active:text-gray-300"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
        </div>
      )}
      <div
        data-testid="media-grid"
        className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 p-4"
      >
        {items.map((item) => (
          <MediaCard key={item.item_id} item={item} />
        ))}
      </div>
    </div>
  )
}
