import { useState, useCallback, useRef, useEffect } from 'react'
import type { TranscriptionSegment } from '../api/types'

/**
 * Binary search for the active segment at a given time (ms).
 * Segments are assumed sorted by start_ms.
 */
function findActiveIndex(segments: TranscriptionSegment[], timeMs: number): number {
  if (segments.length === 0) return -1

  let lo = 0
  let hi = segments.length - 1
  let result = -1

  while (lo <= hi) {
    const mid = (lo + hi) >>> 1
    if (segments[mid].start_ms <= timeMs) {
      result = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }

  // Verify the found segment actually contains the time
  if (result >= 0 && segments[result].end_ms >= timeMs) {
    return result
  }

  return -1
}

export interface UseVideoSyncReturn {
  currentTimeMs: number
  activeSegmentIndex: number
  setCurrentTimeMs: (ms: number) => void
  handleTimeUpdate: (videoEl: HTMLVideoElement) => void
  seekTo: (ms: number, videoEl: HTMLVideoElement | null) => void
}

export function useVideoSync(segments: TranscriptionSegment[]): UseVideoSyncReturn {
  const [currentTimeMs, setCurrentTimeMs] = useState(0)
  const [activeSegmentIndex, setActiveSegmentIndex] = useState(-1)
  const prevIndexRef = useRef(-1)

  const handleTimeUpdate = useCallback(
    (videoEl: HTMLVideoElement) => {
      const ms = Math.round(videoEl.currentTime * 1000)
      setCurrentTimeMs(ms)
      const idx = findActiveIndex(segments, ms)
      if (idx !== prevIndexRef.current) {
        prevIndexRef.current = idx
        setActiveSegmentIndex(idx)
      }
    },
    [segments],
  )

  const seekTo = useCallback((ms: number, videoEl: HTMLVideoElement | null) => {
    if (!videoEl) return
    videoEl.currentTime = ms / 1000
    videoEl.play().catch(() => {})
  }, [])

  // Reset when segments change
  useEffect(() => {
    prevIndexRef.current = -1
    setActiveSegmentIndex(-1)
  }, [segments])

  return { currentTimeMs, activeSegmentIndex, setCurrentTimeMs, handleTimeUpdate, seekTo }
}
