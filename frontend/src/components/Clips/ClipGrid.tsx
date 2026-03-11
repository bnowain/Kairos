import { ClipCard } from './ClipCard'
import { Spinner } from '../ui/Spinner'
import type { Clip } from '../../api/types'

interface ClipGridProps {
  clips: Clip[]
  isLoading: boolean
  error?: Error | null
  emptyMessage?: string
}

export function ClipGrid({ clips, isLoading, error, emptyMessage }: ClipGridProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Spinner size="lg" />
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
      <div className="flex items-center justify-center h-40 text-gray-500">
        <p>{emptyMessage ?? 'No clips yet.'}</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {clips.map((clip) => (
        <ClipCard key={clip.clip_id} clip={clip} />
      ))}
    </div>
  )
}
