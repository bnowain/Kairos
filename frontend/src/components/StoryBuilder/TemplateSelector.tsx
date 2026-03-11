import { Badge } from '../ui/Badge'
import { formatDuration } from '../../utils/format'
import type { StoryTemplate } from '../../api/types'

interface TemplateSelectorProps {
  templates: StoryTemplate[]
  selectedId: string | null
  onSelect: (templateId: string) => void
}

const pacingVariant: Record<string, 'info' | 'warning' | 'success' | 'error' | 'default'> = {
  fast: 'error',
  medium: 'warning',
  slow: 'info',
}

export function TemplateSelector({ templates, selectedId, onSelect }: TemplateSelectorProps) {
  return (
    <div className="flex flex-col gap-2">
      {templates.map((t) => (
        <button
          key={t.template_id}
          onClick={() => onSelect(t.template_id)}
          className={`text-left rounded-lg border p-3 transition-colors ${
            selectedId === t.template_id
              ? 'border-blue-500 bg-blue-600/10'
              : 'border-gray-800 bg-gray-900 hover:border-gray-700'
          }`}
        >
          <div className="flex items-start justify-between gap-2 mb-1">
            <span className="text-sm font-medium text-gray-100">{t.template_name}</span>
            <Badge variant={pacingVariant[t.pacing] ?? 'default'}>{t.pacing}</Badge>
          </div>
          <p className="text-xs text-gray-500 mb-2">{t.description}</p>
          <span className="text-xs text-gray-600 font-mono">
            Target: {formatDuration(t.target_duration_ms)} · {t.aspect_ratio_default}
          </span>
        </button>
      ))}
    </div>
  )
}
