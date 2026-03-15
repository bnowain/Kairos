import { Dialog } from '../ui/Dialog'
import { apiUrl } from '../../api/client'

interface RenderPreviewProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  renderId: string
  outputPath: string
}

export function RenderPreview({ open, onOpenChange, outputPath }: RenderPreviewProps) {
  const filename = outputPath.split('/').pop()
  const src = apiUrl(`/media/renders/${filename}`)

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Render Preview" className="max-w-3xl">
      <div className="aspect-video bg-black rounded-lg overflow-hidden">
        <video
          key={src}
          src={src}
          controls
          autoPlay
          className="w-full h-full object-contain"
        />
      </div>
    </Dialog>
  )
}
