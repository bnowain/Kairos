import { useState } from 'react'
import { Dialog } from '../ui/Dialog'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { useDownloadVideo } from '../../hooks/useLibrary'

interface DownloadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function DownloadDialog({ open, onOpenChange }: DownloadDialogProps) {
  const [url, setUrl] = useState('')
  const { mutate, isPending, error } = useDownloadVideo()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!url.trim()) return
    mutate(url.trim(), {
      onSuccess: () => {
        setUrl('')
        onOpenChange(false)
      },
    })
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Add Video"
      description="Enter a YouTube, Rumble, or other supported URL to download."
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="Video URL"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          autoFocus
        />
        {error && (
          <p className="text-sm text-red-400">{error.message}</p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" loading={isPending} disabled={!url.trim()}>
            Download
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
