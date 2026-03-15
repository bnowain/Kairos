import { useState, useRef, useCallback } from 'react'
import type { ReactNode, DragEvent } from 'react'
import { Upload } from 'lucide-react'

interface DropZoneProps {
  children: ReactNode
  onFileDrop: (file: File) => void
  onUrlDrop: (url: string) => void
  disabled?: boolean
}

export function DropZone({ children, onFileDrop, onUrlDrop, disabled }: DropZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const dragCounter = useRef(0)

  const handleDragEnter = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      if (disabled) return
      dragCounter.current++
      if (dragCounter.current === 1) setIsDragging(true)
    },
    [disabled],
  )

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault()
    dragCounter.current--
    if (dragCounter.current === 0) setIsDragging(false)
  }, [])

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
  }, [])

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      dragCounter.current = 0
      setIsDragging(false)
      if (disabled) return

      // Check for video files first
      const files = e.dataTransfer.files
      if (files.length > 0) {
        const file = files[0]
        if (file.type.startsWith('video/')) {
          onFileDrop(file)
          return
        }
      }

      // Check for URL text
      const text = e.dataTransfer.getData('text/plain')
      if (text && (text.startsWith('http://') || text.startsWith('https://'))) {
        onUrlDrop(text.trim())
      }
    },
    [disabled, onFileDrop, onUrlDrop],
  )

  return (
    <div
      className="relative"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {children}
      {isDragging && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-gray-950/80 border-2 border-dashed border-blue-500 rounded-lg">
          <Upload className="h-10 w-10 text-blue-400" />
          <p className="text-sm font-medium text-blue-300">Drop video files or URLs here</p>
        </div>
      )}
    </div>
  )
}
