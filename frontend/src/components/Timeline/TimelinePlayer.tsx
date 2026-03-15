import { useRef, useEffect } from 'react'
import { X, Play, Pause, SkipForward, SkipBack } from 'lucide-react'
import { Button } from '../ui/Button'
import { useTimelinePlayback } from '../../hooks/useTimelinePlayback'
import { formatDuration } from '../../utils/format'
import type { TimelineElement } from '../../api/types'

interface TimelinePlayerProps {
  elements: TimelineElement[]
  onClose: () => void
}

export function TimelinePlayer({ elements, onClose }: TimelinePlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const {
    currentIndex,
    totalElements,
    isPlaying,
    currentElement,
    currentVideoSrc,
    play,
    pause,
    next,
    prev,
    onEnded,
  } = useTimelinePlayback(elements)

  // Auto-play video when source changes and playing
  useEffect(() => {
    if (isPlaying && videoRef.current && currentVideoSrc) {
      void videoRef.current.play()
    }
  }, [currentVideoSrc, isPlaying])

  const isClip = currentElement?.element_type === 'clip'
  const params = currentElement?.element_params
    ? (JSON.parse(currentElement.element_params) as Record<string, string>)
    : {}

  return (
    <div className="bg-gray-950 border-b border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={prev} disabled={currentIndex === 0}>
              <SkipBack className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={isPlaying ? pause : play}
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="sm" onClick={next} disabled={currentIndex >= totalElements - 1}>
              <SkipForward className="h-4 w-4" />
            </Button>
          </div>
          <span className="text-sm text-gray-400">
            Clip {currentIndex + 1} of {totalElements}
          </span>
          {currentElement && (
            <span className="text-xs text-gray-500 capitalize">
              {currentElement.element_type}
              {' · '}
              {formatDuration(currentElement.duration_ms)}
            </span>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="aspect-video max-h-80 bg-black rounded-lg overflow-hidden mx-auto">
        {isClip && currentVideoSrc ? (
          <video
            ref={videoRef}
            key={currentVideoSrc}
            src={currentVideoSrc}
            className="w-full h-full object-contain"
            controls
            autoPlay={isPlaying}
            onEnded={onEnded}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <div className="text-center">
              <p className="text-lg font-medium capitalize">
                {currentElement?.element_type ?? 'No element'}
              </p>
              {params.text && <p className="text-sm mt-1">{params.text}</p>}
              {params.transition_type && (
                <p className="text-sm mt-1 text-gray-500">{params.transition_type}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
