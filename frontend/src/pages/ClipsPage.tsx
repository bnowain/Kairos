import { useState } from 'react'
import { Scissors } from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { ClipGrid } from '../components/Clips/ClipGrid'
import { Button } from '../components/ui/Button'
import { Select } from '../components/ui/Select'
import { useClips, useBatchExtractClips } from '../hooks/useClips'

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'extracting', label: 'Extracting' },
  { value: 'ready', label: 'Ready' },
  { value: 'error', label: 'Error' },
]

const SOURCE_OPTIONS = [
  { value: '', label: 'All sources' },
  { value: 'ai', label: 'AI Generated' },
  { value: 'manual', label: 'Manual' },
]

export default function ClipsPage() {
  const [status, setStatus] = useState('')
  const [source, setSource] = useState('')
  const [minScore, setMinScore] = useState(0)

  const { data, isLoading, error } = useClips({
    status: status || undefined,
    clip_source: (source as 'ai' | 'manual') || undefined,
    min_score: minScore > 0 ? minScore : undefined,
    page_size: 200,
  })

  const { mutate: batchExtract, isPending: extracting } = useBatchExtractClips()

  const pendingClips = data?.items.filter((c) => c.clip_status === 'pending') ?? []

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title="All Clips"
        actions={
          pendingClips.length > 0 ? (
            <Button
              loading={extracting}
              onClick={() => batchExtract(pendingClips.map((c) => c.clip_id))}
            >
              <Scissors className="h-4 w-4" />
              Batch Extract ({pendingClips.length})
            </Button>
          ) : undefined
        }
      />

      {/* Filters */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-gray-800 flex-wrap">
        <Select
          value={status}
          onValueChange={setStatus}
          options={STATUS_OPTIONS}
          className="w-40"
        />
        <Select
          value={source}
          onValueChange={setSource}
          options={SOURCE_OPTIONS}
          className="w-40"
        />
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-500 whitespace-nowrap">
            Min score: {Math.round(minScore * 100)}%
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={minScore}
            onChange={(e) => setMinScore(parseFloat(e.target.value))}
            className="w-28 accent-blue-500"
          />
        </div>
        <span className="ml-auto text-sm text-gray-500">
          {data?.total ?? 0} clips
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <ClipGrid
          clips={data?.items ?? []}
          isLoading={isLoading}
          error={error}
          emptyMessage="No clips found. Generate clips from an item's detail page."
        />
      </div>
    </div>
  )
}
