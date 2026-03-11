import { useState } from 'react'
import { Plus } from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { MediaGrid } from '../components/Library/MediaGrid'
import { DownloadDialog } from '../components/Library/DownloadDialog'
import { Button } from '../components/ui/Button'
import { useLibrary } from '../hooks/useLibrary'

export default function LibraryPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const { data, isLoading, error } = useLibrary({ page_size: 100 })

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title="Media Library"
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            Add Video
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto">
        <MediaGrid
          items={data?.items ?? []}
          isLoading={isLoading}
          error={error}
        />
      </div>
      <DownloadDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  )
}
