import { MediaCard } from './MediaCard'
import { Spinner } from '../ui/Spinner'
import type { MediaItem } from '../../api/types'

interface MediaGridProps {
  items: MediaItem[]
  isLoading: boolean
  error?: Error | null
}

export function MediaGrid({ items, isLoading, error }: MediaGridProps) {
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
        <p className="text-sm">Click Add Video to get started.</p>
      </div>
    )
  }

  return (
    <div
      data-testid="media-grid"
      className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 p-6"
    >
      {items.map((item) => (
        <MediaCard key={item.item_id} item={item} />
      ))}
    </div>
  )
}
