import { useState } from 'react'
import { Plus, Rss } from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { Button } from '../components/ui/Button'
import { SourceRow } from '../components/Sources/SourceRow'
import { SourceRowSkeleton } from '../components/Sources/SourceRowSkeleton'
import { SourceFormDialog } from '../components/Sources/SourceFormDialog'
import { EmptyState } from '../components/ui/EmptyState'
import { useSources, useDeleteSource, usePollSource } from '../hooks/useSources'
import type { AcquisitionSource } from '../api/types'

export default function SourcesPage() {
  const { data: sources, isLoading, error } = useSources()
  const { mutate: doDelete } = useDeleteSource()
  const { mutate: doPoll, isPending: pollPending, variables: pollVars } = usePollSource()

  const [formOpen, setFormOpen] = useState(false)
  const [editSource, setEditSource] = useState<AcquisitionSource | null>(null)

  function handleEdit(source: AcquisitionSource) {
    setEditSource(source)
    setFormOpen(true)
  }

  function handleAdd() {
    setEditSource(null)
    setFormOpen(true)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title="Sources"
        actions={
          <Button onClick={handleAdd}>
            <Plus className="h-4 w-4" />
            Add Source
          </Button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex flex-col gap-3 max-w-3xl">
            {Array.from({ length: 4 }).map((_, i) => (
              <SourceRowSkeleton key={i} />
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-40 text-red-400">
            <p className="font-medium">Failed to load sources</p>
            <p className="text-sm text-gray-500">{(error as Error).message}</p>
          </div>
        ) : !sources || sources.length === 0 ? (
          <EmptyState
            icon={Rss}
            heading="No sources configured"
            description="Add a source to start automatically polling for new videos."
            action={
              <Button onClick={handleAdd}>
                <Plus className="h-4 w-4" />
                Add Source
              </Button>
            }
          />
        ) : (
          <div className="flex flex-col gap-3 max-w-3xl">
            {sources.map((s) => (
              <SourceRow
                key={s.source_id}
                source={s}
                onEdit={handleEdit}
                onPoll={(id) => doPoll(id)}
                onDelete={(id) => doDelete(id)}
                pollPending={pollPending && pollVars === s.source_id}
              />
            ))}
          </div>
        )}
      </div>

      <SourceFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        source={editSource}
      />
    </div>
  )
}
