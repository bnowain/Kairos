import { useState } from 'react'
import { Plus } from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import { SourceRow } from '../components/Sources/SourceRow'
import { SourceFormDialog } from '../components/Sources/SourceFormDialog'
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
          <div className="flex items-center justify-center h-40">
            <Spinner size="lg" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-40 text-red-400">
            <p className="font-medium">Failed to load sources</p>
            <p className="text-sm text-gray-500">{(error as Error).message}</p>
          </div>
        ) : !sources || sources.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-gray-500">
            <p>No sources configured. Add one to start polling for videos.</p>
          </div>
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
