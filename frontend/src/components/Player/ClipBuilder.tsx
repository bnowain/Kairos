import { useState } from 'react'
import { Scissors, X, Loader2, Check } from 'lucide-react'
import { Button } from '../ui/Button'
import { formatMs } from '../../utils/format'
import { useCreateClip } from '../../hooks/useClips'

interface ClipBuilderProps {
  itemId: string
  currentTimeMs: number
  onRangeChange: (inMs: number | null, outMs: number | null) => void
}

export function ClipBuilder({ itemId, currentTimeMs, onRangeChange }: ClipBuilderProps) {
  const [inMs, setInMs] = useState<number | null>(null)
  const [outMs, setOutMs] = useState<number | null>(null)
  const [title, setTitle] = useState('')
  const [createdClipId, setCreatedClipId] = useState<string | null>(null)

  const { mutate: createClip, isPending } = useCreateClip()

  const setIn = () => {
    const val = Math.round(currentTimeMs)
    setInMs(val)
    setCreatedClipId(null)
    onRangeChange(val, outMs)
  }

  const setOut = () => {
    const val = Math.round(currentTimeMs)
    setOutMs(val)
    setCreatedClipId(null)
    onRangeChange(inMs, val)
  }

  const clear = () => {
    setInMs(null)
    setOutMs(null)
    setTitle('')
    setCreatedClipId(null)
    onRangeChange(null, null)
  }

  const isValid = inMs != null && outMs != null && inMs < outMs && (outMs - inMs) >= 500
  const durationMs = inMs != null && outMs != null ? outMs - inMs : 0

  const handleCreate = () => {
    if (!isValid || inMs == null || outMs == null) return
    createClip(
      {
        item_id: itemId,
        start_ms: inMs,
        end_ms: outMs,
        clip_title: title.trim() || undefined,
      },
      {
        onSuccess: (data) => {
          setCreatedClipId(data.clip_id)
        },
      },
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-2 px-3 py-2 bg-gray-900/80 border-t border-gray-800">
      <Button size="sm" variant="secondary" onClick={setIn}>
        Set In
      </Button>
      <Button size="sm" variant="secondary" onClick={setOut}>
        Set Out
      </Button>

      <div className="flex items-center gap-2 text-xs text-gray-400 font-mono">
        <span>In: {inMs != null ? formatMs(inMs) : '--:--'}</span>
        <span>Out: {outMs != null ? formatMs(outMs) : '--:--'}</span>
        {isValid && <span className="text-gray-300">({formatMs(durationMs)})</span>}
      </div>

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Clip title..."
        className="flex-1 min-w-[120px] max-w-[240px] rounded border border-gray-700 bg-gray-800/50 px-2 py-1 text-xs text-gray-200 placeholder:text-gray-600 focus:border-blue-500 focus:outline-none"
      />

      {createdClipId ? (
        <span className="flex items-center gap-1 text-xs text-green-400">
          <Check className="w-3.5 h-3.5" />
          Clip created
        </span>
      ) : (
        <Button
          size="sm"
          disabled={!isValid || isPending}
          onClick={handleCreate}
        >
          {isPending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Scissors className="w-3.5 h-3.5" />
          )}
          Create Clip
        </Button>
      )}

      {(inMs != null || outMs != null) && (
        <button
          onClick={clear}
          className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
          title="Clear"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}
