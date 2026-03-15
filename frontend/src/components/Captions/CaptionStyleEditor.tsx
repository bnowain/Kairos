import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { CaptionPreview } from './CaptionPreview'
import { createCaptionStyle, updateCaptionStyle } from '../../api/captions'
import type { CaptionStyle } from '../../api/types'

interface CaptionStyleEditorProps {
  style?: CaptionStyle
  onDone: () => void
}

const fontOptions = [
  'Arial',
  'Impact',
  'Roboto',
  'Helvetica',
  'Verdana',
  'Georgia',
  'Courier New',
  'Comic Sans MS',
  'Trebuchet MS',
  'Palatino',
]

const platformOptions = [
  { value: '', label: 'None' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'instagram', label: 'Instagram' },
]

const animationOptions = [
  { value: '', label: 'None' },
  { value: 'word_highlight', label: 'Word Highlight' },
  { value: 'karaoke', label: 'Karaoke' },
  { value: 'typewriter', label: 'Typewriter' },
]

const positionOptions = [
  { value: 'bottom', label: 'Bottom' },
  { value: 'top', label: 'Top' },
  { value: 'middle', label: 'Middle' },
]

export function CaptionStyleEditor({ style, onDone }: CaptionStyleEditorProps) {
  const qc = useQueryClient()
  const isEdit = !!style

  const [styleName, setStyleName] = useState(style?.style_name ?? '')
  const [platformPreset, setPlatformPreset] = useState(style?.platform_preset ?? '')
  const [fontName, setFontName] = useState(style?.font_name ?? 'Arial')
  const [fontSize, setFontSize] = useState(style?.font_size ?? 32)
  const [fontColor, setFontColor] = useState(style?.font_color ?? '#ffffff')
  const [outlineColor, setOutlineColor] = useState(style?.outline_color ?? '#000000')
  const [outlineWidth, setOutlineWidth] = useState(style?.outline_width ?? 2)
  const [shadow, setShadow] = useState(style?.shadow ?? 1)
  const [animationType, setAnimationType] = useState(style?.animation_type ?? '')
  const [position, setPosition] = useState(style?.position ?? 'bottom')

  const createMut = useMutation({
    mutationFn: createCaptionStyle,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['caption-styles'] })
      onDone()
    },
  })

  const updateMut = useMutation({
    mutationFn: (data: Partial<CaptionStyle>) => updateCaptionStyle(style!.style_id, data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['caption-styles'] })
      onDone()
    },
  })

  function handleSave() {
    const data = {
      style_name: styleName,
      platform_preset: platformPreset || null,
      font_name: fontName,
      font_size: fontSize,
      font_color: fontColor,
      outline_color: outlineColor,
      outline_width: outlineWidth,
      shadow,
      animation_type: animationType || null,
      position,
    }

    if (isEdit) {
      updateMut.mutate(data)
    } else {
      createMut.mutate(data as Omit<CaptionStyle, 'style_id' | 'created_at'>)
    }
  }

  const isPending = createMut.isPending || updateMut.isPending

  return (
    <div className="flex flex-col gap-6">
      <CaptionPreview
        fontName={fontName}
        fontSize={fontSize}
        fontColor={fontColor}
        outlineColor={outlineColor}
        outlineWidth={outlineWidth}
        shadow={shadow}
        position={position}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="text-xs text-gray-400">Style Name</label>
          <Input value={styleName} onChange={(e) => setStyleName(e.target.value)} placeholder="My Style" />
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Platform Preset</label>
          <select
            value={platformPreset}
            onChange={(e) => setPlatformPreset(e.target.value)}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200"
          >
            {platformOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Font</label>
          <select
            value={fontName}
            onChange={(e) => setFontName(e.target.value)}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200"
          >
            {fontOptions.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Font Size ({fontSize}px)</label>
          <input
            type="range"
            min={12}
            max={120}
            value={fontSize}
            onChange={(e) => setFontSize(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Font Color</label>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={fontColor}
              onChange={(e) => setFontColor(e.target.value)}
              className="h-9 w-12 rounded border border-gray-700 bg-gray-800 cursor-pointer"
            />
            <span className="text-xs text-gray-400 font-mono">{fontColor}</span>
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Outline Color</label>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={outlineColor}
              onChange={(e) => setOutlineColor(e.target.value)}
              className="h-9 w-12 rounded border border-gray-700 bg-gray-800 cursor-pointer"
            />
            <span className="text-xs text-gray-400 font-mono">{outlineColor}</span>
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Outline Width ({outlineWidth})</label>
          <input
            type="range"
            min={0}
            max={10}
            value={outlineWidth}
            onChange={(e) => setOutlineWidth(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Shadow ({shadow})</label>
          <input
            type="range"
            min={0}
            max={5}
            value={shadow}
            onChange={(e) => setShadow(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Animation</label>
          <select
            value={animationType}
            onChange={(e) => setAnimationType(e.target.value)}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200"
          >
            {animationOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Position</label>
          <select
            value={position}
            onChange={(e) => setPosition(e.target.value)}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200"
          >
            {positionOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex gap-2 justify-end">
        <Button variant="secondary" onClick={onDone}>Cancel</Button>
        <Button onClick={handleSave} loading={isPending} disabled={!styleName.trim()}>
          {isEdit ? 'Update' : 'Create'} Style
        </Button>
      </div>
    </div>
  )
}
