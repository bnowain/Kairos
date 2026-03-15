import { Pencil, RefreshCw, Trash2 } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { formatDateTime } from '../../utils/format'
import type { AcquisitionSource } from '../../api/types'

interface SourceRowProps {
  source: AcquisitionSource
  onEdit: (source: AcquisitionSource) => void
  onPoll: (sourceId: string) => void
  onDelete: (sourceId: string) => void
  pollPending?: boolean
}

const PLATFORM_COLORS: Record<string, string> = {
  youtube: 'bg-red-600/20 text-red-400',
  tiktok: 'bg-pink-600/20 text-pink-400',
  facebook: 'bg-blue-600/20 text-blue-400',
  instagram: 'bg-purple-600/20 text-purple-400',
  rumble: 'bg-green-600/20 text-green-400',
  twitter: 'bg-sky-600/20 text-sky-400',
}

export function SourceRow({ source, onEdit, onPoll, onDelete, pollPending }: SourceRowProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 rounded-lg bg-gray-900 border border-gray-800 p-4">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <span
            className={`inline-block rounded px-2 py-0.5 text-xs font-medium capitalize ${PLATFORM_COLORS[source.platform] ?? 'bg-gray-700 text-gray-300'}`}
          >
            {source.platform}
          </span>
          <span className="text-sm font-medium text-gray-200 truncate">
            {source.source_name || source.source_url}
          </span>
          <Badge variant={source.enabled ? 'success' : 'default'}>
            {source.enabled ? 'Enabled' : 'Disabled'}
          </Badge>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500 flex-wrap">
          <span>Type: {source.source_type}</span>
          <span>Schedule: {source.schedule_cron || 'Manual'}</span>
          <span>Polled: {source.last_polled_at ? formatDateTime(source.last_polled_at) : 'Never'}</span>
          {source.download_quality && <span>Quality: {source.download_quality}</span>}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Button size="sm" variant="ghost" onClick={() => onEdit(source)} aria-label="Edit source">
          <Pencil className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onPoll(source.source_id)}
          loading={pollPending}
          aria-label="Poll now"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            if (window.confirm(`Delete source "${source.source_name || source.source_url}"?`)) {
              onDelete(source.source_id)
            }
          }}
          aria-label="Delete source"
          className="text-red-400 hover:text-red-300"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
