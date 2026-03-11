import { RefreshCw } from 'lucide-react'
import { MediaCard } from './MediaCard'
import { Spinner } from '../ui/Spinner'
import type { MediaItem } from '../../api/types'

interface MediaGridProps {
  items: MediaItem[]
  isLoading: boolean
  error?: Error | null
  onRefresh?: () => void
}

export function MediaGrid({ items, isLoading, error, onRefresh }: MediaGridProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
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
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-gray-500">
        <p className="text-lg font-medium text-gray-400">No videos yet</p>
        <p className="text-sm">Upload a video or click Add Video to get started.</p>
      </div>
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
