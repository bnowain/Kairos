import { apiUrl } from '../../api/client'

interface ClipPlayerProps {
  clipFilePath: string | null
  className?: string
}

export function ClipPlayer({ clipFilePath, className }: ClipPlayerProps) {
  if (!clipFilePath) {
    return (
      <div className="flex items-center justify-center h-32 bg-gray-800 rounded text-gray-500 text-sm">
        No video file available
      </div>
    )
  }

  const filename = clipFilePath.split('/').pop() ?? clipFilePath

  return (
    <video
      className={className}
      controls
      preload="metadata"
      src={apiUrl(`/media/clips/${filename}`)}
    />
  )
}
