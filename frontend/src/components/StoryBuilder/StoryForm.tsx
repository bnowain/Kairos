import { useState } from 'react'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { Button } from '../ui/Button'
import type { MediaItem } from '../../api/types'

interface StoryFormProps {
  items: MediaItem[]
  templateId: string | null
  onGenerate: (params: {
    item_ids: string[]
    story_name: string
    aspect_ratio: string
    pacing_override: string
    min_score: number
  }) => void
  isLoading: boolean
}

const ASPECT_RATIOS = [
  { value: '9:16', label: '9:16 (Vertical / TikTok)' },
  { value: '16:9', label: '16:9 (Landscape)' },
  { value: '1:1', label: '1:1 (Square)' },
  { value: '4:5', label: '4:5 (Instagram)' },
]

const PACING_OPTIONS = [
  { value: '', label: 'Use template default' },
  { value: 'fast', label: 'Fast' },
  { value: 'medium', label: 'Medium' },
  { value: 'slow', label: 'Slow' },
]

export function StoryForm({ items, templateId, onGenerate, isLoading }: StoryFormProps) {
  const [selectedItems, setSelectedItems] = useState<string[]>([])
  const [storyName, setStoryName] = useState('')
  const [aspectRatio, setAspectRatio] = useState('9:16')
  const [pacingOverride, setPacingOverride] = useState('')
  const [minScore, setMinScore] = useState(0.5)

  function toggleItem(id: string) {
    setSelectedItems((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    )
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!templateId || selectedItems.length === 0) return
    onGenerate({
      item_ids: selectedItems,
      story_name: storyName || 'Untitled Story',
      aspect_ratio: aspectRatio,
      pacing_override: pacingOverride,
      min_score: minScore,
    })
  }

  const readyItems = items.filter((i) => i.item_status === 'ready')

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div>
        <label className="text-sm text-gray-400 mb-2 block">Source Videos</label>
        <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto rounded-md border border-gray-700 p-2 bg-gray-800/50">
          {readyItems.length === 0 ? (
            <p className="text-sm text-gray-500 p-2">No ready videos in library</p>
          ) : (
            readyItems.map((item) => (
              <label
                key={item.item_id}
                className="flex items-center gap-2 cursor-pointer rounded px-2 py-1.5 hover:bg-gray-700 transition-colors"
              >
                <input
                  type="checkbox"
                  checked={selectedItems.includes(item.item_id)}
                  onChange={() => toggleItem(item.item_id)}
                  className="accent-blue-500"
                />
                <span className="text-sm text-gray-200 truncate">
                  {item.item_title ?? 'Untitled'}
                </span>
              </label>
            ))
          )}
        </div>
      </div>

      <Input
        label="Story Name"
        placeholder="Untitled Story"
        value={storyName}
        onChange={(e) => setStoryName(e.target.value)}
      />

      <Select
        label="Aspect Ratio"
        value={aspectRatio}
        onValueChange={setAspectRatio}
        options={ASPECT_RATIOS}
      />

      <Select
        label="Pacing Override"
        value={pacingOverride}
        onValueChange={setPacingOverride}
        options={PACING_OPTIONS}
      />

      <div>
        <label className="text-sm text-gray-400 mb-1 block">
          Min Score: {Math.round(minScore * 100)}%
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={minScore}
          onChange={(e) => setMinScore(parseFloat(e.target.value))}
          className="w-full accent-blue-500"
        />
      </div>

      <Button
        type="submit"
        loading={isLoading}
        disabled={!templateId || selectedItems.length === 0}
        className="w-full"
      >
        Generate Story
      </Button>
    </form>
  )
}
