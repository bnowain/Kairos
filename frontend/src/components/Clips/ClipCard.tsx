import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Film, Download, Play, ExternalLink } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { SpeakerBadge } from '../Transcript/SpeakerBadge'
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
  const navigate = useNavigate()
  const [showPlayer, setShowPlayer] = useState(false)
  const filename = clip.clip_file_path?.split('/').pop()
  const thumbFilename = clip.clip_thumb_path?.split('/').pop()

  return (
    <div className="flex flex-col rounded-lg bg-gray-900 border border-gray-800 overflow-hidden">
      {/* Thumbnail / Inline player */}
      <div className="relative aspect-video bg-gray-800 overflow-hidden">
        {showPlayer && clip.clip_status === 'ready' && filename ? (
          <video
            src={apiUrl(`/api/clips/${clip.clip_id}/download`)}
            controls
            autoPlay
            className="w-full h-full object-contain bg-black"
          />
        ) : (
          <>
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
            {clip.clip_status === 'ready' && filename && (
              <button
                onClick={() => setShowPlayer(true)}
                className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 hover:opacity-100 transition-opacity"
              >
                <Play className="h-10 w-10 text-white drop-shadow-lg" />
              </button>
            )}
          </>
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

        {/* Speaker + source video */}
        <div className="flex items-center gap-2 flex-wrap">
          {clip.speaker_label && (
            <SpeakerBadge speaker={clip.speaker_label} />
          )}
          {clip.item_title && (
            <button
              onClick={() => navigate(`/item/${clip.item_id}?tab=transcript&t=${clip.start_ms}`)}
              className="text-xs text-gray-500 hover:text-blue-400 truncate max-w-[160px] flex items-center gap-0.5 transition-colors"
              title={clip.item_title}
            >
              <ExternalLink className="w-3 h-3 shrink-0" />
              {clip.item_title}
            </button>
          )}
        </div>

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
              href={apiUrl(`/api/clips/${clip.clip_id}/download`)}
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
