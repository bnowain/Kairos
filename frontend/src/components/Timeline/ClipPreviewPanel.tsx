import { useQuery } from '@tanstack/react-query'
import { fetchClip } from '../../api/clips'
import { streamUrl } from '../../api/library'
import { apiUrl } from '../../api/client'
import { formatDuration } from '../../utils/format'
import type { TimelineElement } from '../../api/types'

interface ClipPreviewPanelProps {
  element: TimelineElement | null
}

export function ClipPreviewPanel({ element }: ClipPreviewPanelProps) {
  const clipId = element?.element_type === 'clip' ? element.clip_id : null

  const { data: clip } = useQuery({
    queryKey: ['clip', clipId],
    queryFn: () => fetchClip(clipId!),
    enabled: !!clipId,
  })

  if (!element) {
    return (
      <div className="flex items-center justify-center h-full text-gray-600 text-sm">
        Select an element to preview
      </div>
    )
  }

  if (element.element_type !== 'clip' || !clipId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 text-sm gap-2">
        <span className="capitalize text-gray-400">{element.element_type}</span>
        <span>{formatDuration(element.duration_ms)}</span>
      </div>
    )
  }

  if (!clip) {
    return (
      <div className="flex items-center justify-center h-full text-gray-600 text-sm">
        Loading clip...
      </div>
    )
  }

  const startSec = clip.start_ms / 1000
  const endSec = clip.end_ms / 1000
  const videoSrc = clip.clip_file_path
    ? apiUrl(`/media/clips/${clip.clip_file_path.split('/').pop()}`)
    : `${streamUrl(clip.item_id)}#t=${startSec},${endSec}`

  return (
    <div className="flex flex-col gap-3">
      <div className="aspect-video bg-black rounded-lg overflow-hidden">
        <video
          key={videoSrc}
          src={videoSrc}
          controls
          className="w-full h-full object-contain"
        />
      </div>
      <div className="space-y-1 text-xs text-gray-400">
        {clip.clip_title && (
          <p className="text-sm text-gray-200 font-medium truncate">{clip.clip_title}</p>
        )}
        <p>Duration: {formatDuration(clip.duration_ms)}</p>
        <p>Source: {clip.item_title ?? clip.item_id.slice(0, 8)}</p>
        <p className="capitalize">Status: {clip.clip_status}</p>
      </div>
    </div>
  )
}
