import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchClip } from '../api/clips'
import { streamUrl } from '../api/library'
import { apiUrl } from '../api/client'
import type { TimelineElement, Clip } from '../api/types'

interface PlaybackState {
  currentIndex: number
  totalElements: number
  isPlaying: boolean
  currentElement: TimelineElement | null
  currentVideoSrc: string | null
  play: () => void
  pause: () => void
  next: () => void
  prev: () => void
  onEnded: () => void
}

export function useTimelinePlayback(elements: TimelineElement[]): PlaybackState {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  const clipElements = elements.filter((e) => e.element_type === 'clip')
  const allClipIds = clipElements.map((e) => e.clip_id).filter(Boolean) as string[]

  // Fetch all clips data
  const { data: clipsMap } = useQuery({
    queryKey: ['timeline-playback-clips', allClipIds.join(',')],
    queryFn: async () => {
      const results = await Promise.all(allClipIds.map((id) => fetchClip(id)))
      const map = new Map<string, Clip>()
      results.forEach((c) => map.set(c.clip_id, c))
      return map
    },
    enabled: allClipIds.length > 0,
  })

  const currentElement = elements[currentIndex] ?? null

  const getVideoSrc = useCallback(
    (el: TimelineElement): string | null => {
      if (el.element_type !== 'clip' || !el.clip_id || !clipsMap) return null
      const clip = clipsMap.get(el.clip_id)
      if (!clip) return null
      if (clip.clip_file_path) {
        return apiUrl(`/media/clips/${clip.clip_file_path.split('/').pop()}`)
      }
      const startSec = clip.start_ms / 1000
      const endSec = clip.end_ms / 1000
      return `${streamUrl(clip.item_id)}#t=${startSec},${endSec}`
    },
    [clipsMap],
  )

  const currentVideoSrc = currentElement ? getVideoSrc(currentElement) : null

  // For non-clip elements, auto-advance after their duration
  useEffect(() => {
    if (!isPlaying || !currentElement) return
    if (currentElement.element_type === 'clip') return // video handles its own end

    const duration = Math.max(currentElement.duration_ms, 2000) // min 2s for slates
    timerRef.current = setTimeout(() => {
      if (currentIndex < elements.length - 1) {
        setCurrentIndex((i) => i + 1)
      } else {
        setIsPlaying(false)
      }
    }, duration)

    return () => clearTimeout(timerRef.current)
  }, [isPlaying, currentElement, currentIndex, elements.length])

  const play = useCallback(() => setIsPlaying(true), [])
  const pause = useCallback(() => setIsPlaying(false), [])

  const next = useCallback(() => {
    if (currentIndex < elements.length - 1) {
      setCurrentIndex((i) => i + 1)
    }
  }, [currentIndex, elements.length])

  const prev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1)
    }
  }, [currentIndex])

  const onEnded = useCallback(() => {
    if (currentIndex < elements.length - 1) {
      setCurrentIndex((i) => i + 1)
    } else {
      setIsPlaying(false)
    }
  }, [currentIndex, elements.length])

  return {
    currentIndex,
    totalElements: elements.length,
    isPlaying,
    currentElement,
    currentVideoSrc,
    play,
    pause,
    next,
    prev,
    onEnded,
  }
}
