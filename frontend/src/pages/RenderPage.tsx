import { useState } from 'react'
import { Plus } from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { RenderQueue } from '../components/Render/RenderQueue'
import { RenderDialog } from '../components/Render/RenderDialog'
import { Button } from '../components/ui/Button'
import { useRenderJobs } from '../hooks/useRender'

export default function RenderPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const { data: jobs = [], isLoading, error } = useRenderJobs()

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title="Render Queue"
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            New Render
          </Button>
        }
      />
      <div className="flex-1 overflow-y-auto p-6">
        <RenderQueue jobs={jobs} isLoading={isLoading} error={error} />
      </div>
      <RenderDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  )
}
