import { useRef, useEffect, useState, useCallback } from 'react'
import { streamUrl } from '../../api/library'
import { useVideoSync } from '../../hooks/useVideoSync'
import { TranscriptPanel } from './TranscriptPanel'
import { ClipBuilder } from './ClipBuilder'
import type { TranscriptionSegment } from '../../api/types'

interface SyncedPlayerProps {
  itemId: string
  segments: TranscriptionSegment[]
  initialTimeMs?: number
}

export function SyncedPlayer({ itemId, segments, initialTimeMs }: SyncedPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [clipInMs, setClipInMs] = useState<number | null>(null)
  const [clipOutMs, setClipOutMs] = useState<number | null>(null)
  const initialSeeked = useRef(false)

  const { currentTimeMs, activeSegmentIndex, handleTimeUpdate, seekTo } =
    useVideoSync(segments)

  // Seek to initial time on mount
  useEffect(() => {
    if (initialTimeMs != null && !initialSeeked.current && videoRef.current) {
      initialSeeked.current = true
      // Wait for video to be ready enough to seek
      const video = videoRef.current
      const doSeek = () => {
        video.currentTime = initialTimeMs / 1000
        video.play().catch(() => {})
      }
      if (video.readyState >= 1) {
        doSeek()
      } else {
        video.addEventListener('loadedmetadata', doSeek, { once: true })
      }
    }
  }, [initialTimeMs])

  const onTimeUpdate = useCallback(() => {
    if (videoRef.current) handleTimeUpdate(videoRef.current)
  }, [handleTimeUpdate])

  const handleSegmentClick = useCallback(
    (seg: TranscriptionSegment) => {
      seekTo(seg.start_ms, videoRef.current)
    },
    [seekTo],
  )

  const handleRangeChange = useCallback((inMs: number | null, outMs: number | null) => {
    setClipInMs(inMs)
    setClipOutMs(outMs)
  }, [])

  return (
    <div className="flex flex-col h-full">
      {/* Main content: video + transcript */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden min-h-0">
        {/* Video */}
        <div className="w-full md:w-3/5 flex flex-col shrink-0">
          <div className="relative bg-black">
            <video
              ref={videoRef}
              src={streamUrl(itemId)}
              controls
              preload="metadata"
              onTimeUpdate={onTimeUpdate}
              className="w-full aspect-video"
            />
          </div>
        </div>

        {/* Transcript */}
        <div className="flex-1 min-h-0 overflow-hidden border-l border-gray-800">
          <TranscriptPanel
            segments={segments}
            activeSegmentIndex={activeSegmentIndex}
            clipInMs={clipInMs}
            clipOutMs={clipOutMs}
            itemId={itemId}
            onSegmentClick={handleSegmentClick}
          />
        </div>
      </div>

      {/* Clip builder bar */}
      <ClipBuilder
        itemId={itemId}
        currentTimeMs={currentTimeMs}
        onRangeChange={handleRangeChange}
      />
    </div>
  )
}
