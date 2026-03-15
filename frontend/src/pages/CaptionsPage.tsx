import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Edit2, Type } from 'lucide-react'
import { fetchCaptionStyles, deleteCaptionStyle } from '../api/captions'
import { CaptionStyleEditor } from '../components/Captions/CaptionStyleEditor'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import type { CaptionStyle } from '../api/types'

export default function CaptionsPage() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<CaptionStyle | null>(null)
  const [creating, setCreating] = useState(false)

  const { data: styles, isLoading } = useQuery({
    queryKey: ['caption-styles'],
    queryFn: fetchCaptionStyles,
  })

  const deleteMut = useMutation({
    mutationFn: deleteCaptionStyle,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['caption-styles'] }),
  })

  if (editing || creating) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-800 bg-gray-950">
          <Type className="h-5 w-5 text-gray-400" />
          <h1 className="text-base font-semibold text-gray-100">
            {editing ? 'Edit Caption Style' : 'New Caption Style'}
          </h1>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          <CaptionStyleEditor
            style={editing ?? undefined}
            onDone={() => {
              setEditing(null)
              setCreating(false)
            }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-950">
        <div className="flex items-center gap-3">
          <Type className="h-5 w-5 text-gray-400" />
          <h1 className="text-base font-semibold text-gray-100">Caption Styles</h1>
        </div>
        <Button size="sm" onClick={() => setCreating(true)}>
          <Plus className="h-4 w-4" />
          New Style
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner size="lg" /></div>
        ) : !styles?.length ? (
          <div className="text-center text-gray-500 py-12">
            <Type className="h-10 w-10 mx-auto mb-3 text-gray-700" />
            <p>No caption styles yet.</p>
            <p className="text-sm mt-1">Create one to use when rendering videos.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {styles.map((s) => (
              <div
                key={s.style_id}
                className="rounded-lg bg-gray-900 border border-gray-800 p-4 flex flex-col gap-3 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-100">{s.style_name}</p>
                    {s.platform_preset && (
                      <span className="text-xs text-gray-500 capitalize">{s.platform_preset}</span>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setEditing(s)}>
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-red-500 hover:text-red-400"
                      onClick={() => deleteMut.mutate(s.style_id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>

                {/* Mini preview */}
                <div className="aspect-video bg-gray-950 rounded border border-gray-800 flex items-end justify-center p-2">
                  <p
                    className="text-center text-sm truncate"
                    style={{
                      fontFamily: s.font_name,
                      color: s.font_color,
                      textShadow: s.outline_width > 0
                        ? `${s.outline_width}px ${s.outline_width}px 0 ${s.outline_color}`
                        : undefined,
                    }}
                  >
                    Sample text
                  </p>
                </div>

                <div className="flex flex-wrap gap-1.5 text-xs text-gray-500">
                  <span>{s.font_name}</span>
                  <span>·</span>
                  <span>{s.font_size}px</span>
                  <span>·</span>
                  <span className="capitalize">{s.position}</span>
                  {s.animation_type && (
                    <>
                      <span>·</span>
                      <span className="capitalize">{s.animation_type.replace('_', ' ')}</span>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
