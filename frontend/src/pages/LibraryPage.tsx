import { useRef, useState, useCallback } from 'react'
import { Plus, Upload } from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { MediaGrid } from '../components/Library/MediaGrid'
import { DownloadDialog } from '../components/Library/DownloadDialog'
import { DropZone } from '../components/Library/DropZone'
import { Button } from '../components/ui/Button'
import { useLibrary, useUploadVideo } from '../hooks/useLibrary'

export default function LibraryPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dropUrl, setDropUrl] = useState<string | undefined>()
  const { data, isLoading, error, refetch } = useLibrary({ page_size: 100 })
  const { upload, uploadProgress, isUploading, uploadError } = useUploadVideo()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileDrop = useCallback(
    (file: File) => void upload(file),
    [upload],
  )

  const handleUrlDrop = useCallback((url: string) => {
    setDropUrl(url)
    setDialogOpen(true)
  }, [])

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    void upload(file)
    // Reset so the same file can be re-selected if needed
    e.target.value = ''
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title="Media Library"
        actions={
          <div className="flex items-center gap-2">
            {/* Camera roll upload — primary action on mobile */}
            <Button
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              aria-label="Upload from device"
            >
              <Upload className="h-4 w-4" />
              <span className="hidden sm:inline">
                {isUploading ? `Uploading ${uploadProgress}%` : 'Upload'}
              </span>
            </Button>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">Add Video</span>
            </Button>
          </div>
        }
      />

      {/* Upload progress bar */}
      {isUploading && (
        <div className="h-1 bg-gray-800">
          <div
            className="h-full bg-blue-500 transition-all duration-200"
            style={{ width: `${uploadProgress}%` }}
          />
        </div>
      )}

      {/* Upload error */}
      {uploadError && (
        <div className="px-4 py-2 bg-red-950/40 border-b border-red-900/30 text-sm text-red-400">
          Upload failed: {uploadError}
        </div>
      )}

      <DropZone onFileDrop={handleFileDrop} onUrlDrop={handleUrlDrop} disabled={isUploading}>
        <div className="flex-1 overflow-y-auto">
          <MediaGrid
            items={data?.items ?? []}
            isLoading={isLoading}
            error={error}
            onRefresh={() => void refetch()}
            emptyAction={
              <div className="flex items-center gap-2">
                <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="h-4 w-4" />
                  Upload
                </Button>
                <Button onClick={() => setDialogOpen(true)}>
                  <Plus className="h-4 w-4" />
                  Add Video
                </Button>
              </div>
            }
          />
        </div>
      </DropZone>

      {/* Hidden file input — accepts any video, triggers camera roll on mobile */}
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={handleFileChange}
      />

      <DownloadDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open)
          if (!open) setDropUrl(undefined)
        }}
        defaultUrl={dropUrl}
      />
    </div>
  )
}
