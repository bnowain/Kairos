import { useState, useMemo, useEffect } from 'react'
import { Scissors, Trash2 } from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { ClipGrid } from '../components/Clips/ClipGrid'
import { Button } from '../components/ui/Button'
import { Select } from '../components/ui/Select'
import { Input } from '../components/ui/Input'
import { useClips, useBatchExtractClips, useBulkDeleteClips } from '../hooks/useClips'

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

const SORT_OPTIONS = [
  { value: '', label: 'Default' },
  { value: 'score_high', label: 'Score (high to low)' },
  { value: 'score_low', label: 'Score (low to high)' },
  { value: 'duration_long', label: 'Duration (longest)' },
  { value: 'duration_short', label: 'Duration (shortest)' },
  { value: 'newest', label: 'Newest first' },
  { value: 'oldest', label: 'Oldest first' },
]

export default function ClipsPage() {
  const [status, setStatus] = useState('')
  const [source, setSource] = useState('')
  const [minScore, setMinScore] = useState(0)
  const [speakerFilter, setSpeakerFilter] = useState('')
  const [sourceVideoFilter, setSourceVideoFilter] = useState('')
  const [sortBy, setSortBy] = useState('')
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const { data, isLoading, error } = useClips({
    status: status || undefined,
    clip_source: (source as 'ai' | 'manual') || undefined,
    min_score: minScore > 0 ? minScore : undefined,
    page_size: 200,
  })

  const { mutate: batchExtract, isPending: extracting } = useBatchExtractClips()
  const { mutate: bulkDelete, isPending: deleting } = useBulkDeleteClips()

  // Client-side filtering + sorting
  const filteredClips = useMemo(() => {
    let clips = data?.items ?? []
    if (speakerFilter) {
      const lower = speakerFilter.toLowerCase()
      clips = clips.filter((c) => c.speaker_label?.toLowerCase().includes(lower))
    }
    if (sourceVideoFilter) {
      const lower = sourceVideoFilter.toLowerCase()
      clips = clips.filter((c) => c.item_title?.toLowerCase().includes(lower))
    }
    if (sortBy) {
      clips = [...clips].sort((a, b) => {
        switch (sortBy) {
          case 'score_high': return (b.virality_score ?? 0) - (a.virality_score ?? 0)
          case 'score_low': return (a.virality_score ?? 0) - (b.virality_score ?? 0)
          case 'duration_long': return b.duration_ms - a.duration_ms
          case 'duration_short': return a.duration_ms - b.duration_ms
          case 'newest': return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          case 'oldest': return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          default: return 0
        }
      })
    }
    return clips
  }, [data?.items, speakerFilter, sourceVideoFilter, sortBy])

  // Clear selection when filters/sort change
  useEffect(() => {
    setSelected(new Set())
  }, [status, source, minScore, speakerFilter, sourceVideoFilter, sortBy])

  const pendingClips = data?.items.filter((c) => c.clip_status === 'pending') ?? []

  function toggleSelect(clipId: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(clipId)) next.delete(clipId)
      else next.add(clipId)
      return next
    })
  }

  function toggleSelectAll() {
    if (selected.size === filteredClips.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(filteredClips.map((c) => c.clip_id)))
    }
  }

  function handleBulkDelete() {
    if (selected.size === 0) return
    if (!window.confirm(`Delete ${selected.size} clip(s)? This cannot be undone.`)) return
    bulkDelete([...selected], {
      onSuccess: () => setSelected(new Set()),
    })
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar
        title="All Clips"
        actions={
          <div className="flex items-center gap-2">
            {selected.size > 0 && (
              <>
                <Button size="sm" variant="ghost" onClick={toggleSelectAll}>
                  {selected.size === filteredClips.length ? 'Clear' : 'Select All'}
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  loading={deleting}
                  onClick={handleBulkDelete}
                  className="text-red-400 hover:text-red-300"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete Selected ({selected.size})
                </Button>
              </>
            )}
            {pendingClips.length > 0 && (
              <Button
                loading={extracting}
                onClick={() => batchExtract(pendingClips.map((c) => c.clip_id))}
              >
                <Scissors className="h-4 w-4" />
                Batch Extract ({pendingClips.length})
              </Button>
            )}
          </div>
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
        <Select
          value={sortBy}
          onValueChange={setSortBy}
          options={SORT_OPTIONS}
          className="w-44"
        />
        <Input
          placeholder="Speaker..."
          value={speakerFilter}
          onChange={(e) => setSpeakerFilter(e.target.value)}
          className="w-32"
        />
        <Input
          placeholder="Source video..."
          value={sourceVideoFilter}
          onChange={(e) => setSourceVideoFilter(e.target.value)}
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
          {filteredClips.length} clips
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <ClipGrid
          clips={filteredClips}
          isLoading={isLoading}
          error={error}
          emptyMessage="No clips found. Generate clips from an item's detail page."
          selectable
          selectedIds={selected}
          onToggleSelect={toggleSelect}
        />
      </div>
    </div>
  )
}
