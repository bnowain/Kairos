import { useState } from 'react'
import { Dialog } from '../ui/Dialog'
import { Select } from '../ui/Select'
import { Button } from '../ui/Button'
import { useQuery } from '@tanstack/react-query'
import { fetchTimelines } from '../../api/stories'
import { fetchCaptionStyles } from '../../api/captions'
import { useCreateRenderJob } from '../../hooks/useRender'
import type { CreateRenderParams } from '../../api/render'

interface RenderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function RenderDialog({ open, onOpenChange }: RenderDialogProps) {
  const [timelineId, setTimelineId] = useState('')
  const [quality, setQuality] = useState<'preview' | 'final'>('preview')
  const [addCaptions, setAddCaptions] = useState(false)
  const [captionStyleId, setCaptionStyleId] = useState('')

  const { data: timelines = [] } = useQuery({
    queryKey: ['timelines'],
    queryFn: fetchTimelines,
  })

  const { data: captionStyles = [] } = useQuery({
    queryKey: ['caption-styles'],
    queryFn: fetchCaptionStyles,
  })

  const { mutate: createJob, isPending, error } = useCreateRenderJob()

  const timelineOptions = timelines.map((t) => ({
    value: t.timeline_id,
    label: t.timeline_name,
  }))

  const captionOptions = captionStyles.map((s) => ({
    value: s.style_id,
    label: s.style_name,
  }))

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!timelineId) return
    const params: CreateRenderParams = {
      timeline_id: timelineId,
      render_quality: quality,
    }
    if (addCaptions && captionStyleId) {
      params.add_captions = true
      params.caption_style_id = captionStyleId
    }
    createJob(params, {
      onSuccess: () => onOpenChange(false),
    })
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="New Render Job"
      description="Configure and submit a render job."
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Select
          label="Timeline"
          value={timelineId}
          onValueChange={setTimelineId}
          options={timelineOptions}
          placeholder="Select a timeline..."
        />

        <Select
          label="Quality"
          value={quality}
          onValueChange={(v) => setQuality(v as 'preview' | 'final')}
          options={[
            { value: 'preview', label: 'Preview (fast)' },
            { value: 'final', label: 'Final (high quality)' },
          ]}
        />

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={addCaptions}
            onChange={(e) => setAddCaptions(e.target.checked)}
            className="accent-blue-500"
          />
          <span className="text-sm text-gray-300">Add Captions</span>
        </label>

        {addCaptions && (
          <Select
            label="Caption Style"
            value={captionStyleId}
            onValueChange={setCaptionStyleId}
            options={captionOptions}
            placeholder="Select a style..."
          />
        )}

        {error && <p className="text-sm text-red-400">{error.message}</p>}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" loading={isPending} disabled={!timelineId}>
            Start Render
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
