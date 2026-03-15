import { useState, useEffect } from 'react'
import { Dialog } from '../ui/Dialog'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { Button } from '../ui/Button'
import { useCreateSource, useUpdateSource } from '../../hooks/useSources'
import type { AcquisitionSource } from '../../api/types'

interface SourceFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  source?: AcquisitionSource | null
}

const SOURCE_TYPE_OPTIONS = [
  { value: 'youtube_channel', label: 'YouTube Channel' },
  { value: 'youtube_playlist', label: 'YouTube Playlist' },
  { value: 'tiktok_user', label: 'TikTok User' },
  { value: 'facebook_page', label: 'Facebook Page' },
  { value: 'instagram_profile', label: 'Instagram Profile' },
  { value: 'rumble_channel', label: 'Rumble Channel' },
  { value: 'twitter_user', label: 'Twitter/X User' },
  { value: 'rss_feed', label: 'RSS Feed' },
]

const QUALITY_OPTIONS = [
  { value: '', label: 'Default' },
  { value: 'best', label: 'Best' },
  { value: '1080p', label: '1080p' },
  { value: '720p', label: '720p' },
  { value: '480p', label: '480p' },
]

function platformFromType(sourceType: string): string {
  const map: Record<string, string> = {
    youtube_channel: 'youtube',
    youtube_playlist: 'youtube',
    tiktok_user: 'tiktok',
    facebook_page: 'facebook',
    instagram_profile: 'instagram',
    rumble_channel: 'rumble',
    twitter_user: 'twitter',
    rss_feed: 'rss',
  }
  return map[sourceType] ?? 'other'
}

export function SourceFormDialog({ open, onOpenChange, source }: SourceFormDialogProps) {
  const isEdit = !!source
  const { mutate: create, isPending: creating } = useCreateSource()
  const { mutate: update, isPending: updating } = useUpdateSource()

  const [sourceType, setSourceType] = useState('youtube_channel')
  const [sourceUrl, setSourceUrl] = useState('')
  const [sourceName, setSourceName] = useState('')
  const [scheduleCron, setScheduleCron] = useState('')
  const [downloadQuality, setDownloadQuality] = useState('')
  const [enabled, setEnabled] = useState(true)

  useEffect(() => {
    if (source) {
      setSourceType(source.source_type)
      setSourceUrl(source.source_url)
      setSourceName(source.source_name ?? '')
      setScheduleCron(source.schedule_cron ?? '')
      setDownloadQuality(source.download_quality ?? '')
      setEnabled(!!source.enabled)
    } else {
      setSourceType('youtube_channel')
      setSourceUrl('')
      setSourceName('')
      setScheduleCron('')
      setDownloadQuality('')
      setEnabled(true)
    }
  }, [source, open])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (isEdit) {
      update(
        {
          sourceId: source!.source_id,
          body: {
            source_name: sourceName || undefined,
            schedule_cron: scheduleCron || undefined,
            enabled: enabled ? 1 : 0,
            download_quality: downloadQuality || undefined,
          },
        },
        { onSuccess: () => onOpenChange(false) },
      )
    } else {
      create(
        {
          source_type: sourceType,
          source_url: sourceUrl,
          source_name: sourceName || undefined,
          platform: platformFromType(sourceType),
          schedule_cron: scheduleCron || undefined,
          enabled: enabled ? 1 : 0,
          download_quality: downloadQuality || undefined,
        },
        { onSuccess: () => onOpenChange(false) },
      )
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={isEdit ? 'Edit Source' : 'Add Source'}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {isEdit ? (
          <div className="text-sm text-gray-400">
            <span className="capitalize font-medium text-gray-300">{source!.source_type}</span>
            {' — '}
            <span className="break-all">{source!.source_url}</span>
          </div>
        ) : (
          <>
            <Select
              label="Source Type"
              value={sourceType}
              onValueChange={setSourceType}
              options={SOURCE_TYPE_OPTIONS}
            />
            <Input
              label="URL"
              placeholder="https://youtube.com/@channel"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              required
            />
          </>
        )}
        <Input
          label="Name (optional)"
          placeholder="My Source"
          value={sourceName}
          onChange={(e) => setSourceName(e.target.value)}
        />
        <Input
          label="Cron Schedule (optional)"
          placeholder="0 */6 * * *"
          value={scheduleCron}
          onChange={(e) => setScheduleCron(e.target.value)}
        />
        <Select
          label="Download Quality"
          value={downloadQuality}
          onValueChange={setDownloadQuality}
          options={QUALITY_OPTIONS}
        />
        <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="accent-blue-500"
          />
          Enabled
        </label>
        <div className="flex justify-end gap-2 mt-2">
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" loading={creating || updating}>
            {isEdit ? 'Save' : 'Add Source'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
