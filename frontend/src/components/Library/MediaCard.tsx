import { useNavigate } from 'react-router-dom'
import { Film, AlertCircle, Clock, User } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { apiUrl } from '../../api/client'
import { formatDurationSeconds, formatScore } from '../../utils/format'
import type { MediaItem } from '../../api/types'

interface MediaCardProps {
  item: MediaItem
}

const statusVariant: Record<string, 'default' | 'info' | 'warning' | 'success' | 'error'> = {
  queued: 'default',
  downloading: 'info',
  downloaded: 'info',
  ingesting: 'warning',
  ready: 'success',
  error: 'error',
}

const statusLabel: Record<string, string> = {
  queued: 'Queued',
  downloading: 'Downloading',
  downloaded: 'Downloaded',
  ingesting: 'Ingesting',
  ready: 'Ready',
  error: 'Error',
}

export function MediaCard({ item }: MediaCardProps) {
  const navigate = useNavigate()

  const viralityScore =
    typeof item.virality_score === 'number' ? item.virality_score : null

  return (
    <div
      className="group flex flex-row sm:flex-col rounded-lg bg-gray-900 border border-gray-800 overflow-hidden cursor-pointer hover:border-gray-600 transition-colors"
      onClick={() => navigate(`/item/${item.item_id}`)}
    >
      {/* Thumbnail — horizontal strip on mobile, aspect-video on sm+ */}
      <div className="relative w-28 shrink-0 sm:w-auto sm:aspect-video bg-gray-800 overflow-hidden">
        {item.thumb_path ? (
          <img
            src={apiUrl(`/media/thumbs/${item.thumb_path.split('/').pop()}`)}
            alt={item.item_title ?? 'Video thumbnail'}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              ;(e.target as HTMLImageElement).style.display = 'none'
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <Film className="h-8 w-8 sm:h-10 sm:w-10 text-gray-600" />
          </div>
        )}
        {item.duration_seconds != null && (
          <span className="absolute bottom-1 right-1 rounded bg-black/70 px-1 py-0.5 text-xs text-white font-mono">
            {formatDurationSeconds(item.duration_seconds)}
          </span>
        )}
        {item.item_status === 'error' && (
          <div className="absolute inset-0 flex items-center justify-center bg-red-950/60">
            <AlertCircle className="h-6 w-6 sm:h-8 sm:w-8 text-red-400" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col gap-1 sm:gap-1.5 p-3 flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-100 line-clamp-2 leading-snug">
          {item.item_title ?? 'Untitled'}
        </p>

        {item.item_channel && (
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <User className="h-3 w-3 shrink-0" />
            <span className="truncate">{item.item_channel}</span>
          </div>
        )}

        <div className="flex items-center justify-between mt-auto pt-1">
          <Badge variant={statusVariant[item.item_status] ?? 'default'}>
            {statusLabel[item.item_status] ?? item.item_status}
          </Badge>

          <div className="flex items-center gap-2">
            {item.published_at && (
              <div className="flex items-center gap-1 text-xs text-gray-600">
                <Clock className="h-3 w-3" />
                {new Date(item.published_at).getFullYear()}
              </div>
            )}
            {viralityScore != null && (
              <span className="text-xs font-medium text-green-400">
                {formatScore(viralityScore)}
              </span>
            )}
          </div>
        </div>

        {item.error_msg && (
          <p className="text-xs text-red-400 truncate" title={item.error_msg}>
            {item.error_msg}
          </p>
        )}
      </div>
    </div>
  )
}
