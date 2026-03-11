import { Film, Download, Play } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { apiUrl } from '../../api/client'
import { formatDuration, formatScore } from '../../utils/format'
import { useExtractClip } from '../../hooks/useClips'
import type { Clip } from '../../api/types'

interface ClipCardProps {
  clip: Clip
}

const statusVariant: Record<string, 'default' | 'info' | 'warning' | 'success' | 'error'> = {
  pending: 'default',
  extracting: 'info',
  ready: 'success',
  error: 'error',
}

export function ClipCard({ clip }: ClipCardProps) {
  const { mutate: extract, isPending } = useExtractClip()
  const filename = clip.clip_file_path?.split('/').pop()
  const thumbFilename = clip.clip_thumb_path?.split('/').pop()

  return (
    <div className="flex flex-col rounded-lg bg-gray-900 border border-gray-800 overflow-hidden">
      {/* Thumbnail */}
      <div className="relative aspect-video bg-gray-800 overflow-hidden">
        {thumbFilename ? (
          <img
            src={apiUrl(`/media/thumbs/${thumbFilename}`)}
            alt={clip.clip_title ?? 'Clip'}
            className="w-full h-full object-cover"
            onError={(e) => {
              ;(e.target as HTMLImageElement).style.display = 'none'
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <Film className="h-8 w-8 text-gray-600" />
          </div>
        )}
        <span className="absolute bottom-1.5 right-1.5 rounded bg-black/70 px-1.5 py-0.5 text-xs text-white font-mono">
          {formatDuration(clip.duration_ms)}
        </span>
      </div>

      {/* Content */}
      <div className="flex flex-col gap-2 p-3">
        <p className="text-sm font-medium text-gray-200 line-clamp-2">
          {clip.clip_title ?? 'Untitled Clip'}
        </p>

        <div className="flex items-center justify-between">
          <Badge variant={statusVariant[clip.clip_status] ?? 'default'}>
            {clip.clip_status}
          </Badge>
          {clip.virality_score != null && (
            <span className="text-xs font-medium text-green-400">
              {formatScore(clip.virality_score)}
            </span>
          )}
        </div>

        {clip.clip_transcript && (
          <p className="text-xs text-gray-500 line-clamp-2">{clip.clip_transcript}</p>
        )}

        <div className="flex gap-2 mt-1">
          {clip.clip_status === 'pending' && (
            <Button
              size="sm"
              variant="secondary"
              loading={isPending}
              onClick={() => extract(clip.clip_id)}
              className="flex-1"
            >
              <Play className="h-3.5 w-3.5" />
              Extract
            </Button>
          )}
          {clip.clip_status === 'ready' && filename && (
            <a
              href={apiUrl(`/media/clips/${filename}`)}
              download
              className="flex-1"
            >
              <Button size="sm" variant="ghost" className="w-full">
                <Download className="h-3.5 w-3.5" />
                Download
              </Button>
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
