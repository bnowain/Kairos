import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { TopBar } from '../components/Layout/TopBar'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { StylePicker } from '../components/Captions/StylePicker'
import { Spinner } from '../components/ui/Spinner'
import { fetchHealth, fetchConfig } from '../api/acquisition'
import { fetchCaptionStyles, createCaptionStyle } from '../api/captions'
import type { CaptionStyle } from '../api/types'

const POSITION_OPTIONS = [
  { value: 'bottom', label: 'Bottom' },
  { value: 'top', label: 'Top' },
  { value: 'center', label: 'Center' },
]

const ANIMATION_OPTIONS = [
  { value: '', label: 'None' },
  { value: 'fade', label: 'Fade' },
  { value: 'slide', label: 'Slide' },
  { value: 'pop', label: 'Pop' },
]

function NewStyleForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('')
  const [platform, setPlatform] = useState('')
  const [fontName, setFontName] = useState('Arial')
  const [fontSize, setFontSize] = useState(32)
  const [fontColor, setFontColor] = useState('#FFFFFF')
  const [outlineColor, setOutlineColor] = useState('#000000')
  const [outlineWidth, setOutlineWidth] = useState(2)
  const [position, setPosition] = useState('bottom')
  const [animationType, setAnimationType] = useState('')

  const { mutate, isPending, error } = useMutation({
    mutationFn: (style: Omit<CaptionStyle, 'style_id' | 'created_at'>) =>
      createCaptionStyle(style),
    onSuccess: () => {
      onCreated()
      setName('')
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    mutate({
      style_name: name.trim(),
      platform_preset: platform || null,
      font_name: fontName,
      font_size: fontSize,
      font_color: fontColor,
      outline_color: outlineColor,
      outline_width: outlineWidth,
      shadow: 0,
      animation_type: animationType || null,
      position,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3">
      <Input
        label="Style Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="My Caption Style"
        className="col-span-2"
      />
      <Input
        label="Platform Preset"
        value={platform}
        onChange={(e) => setPlatform(e.target.value)}
        placeholder="TikTok, YouTube..."
      />
      <Input
        label="Font"
        value={fontName}
        onChange={(e) => setFontName(e.target.value)}
      />
      <div>
        <label className="text-sm text-gray-400 mb-1 block">Font Size: {fontSize}px</label>
        <input
          type="range"
          min="16"
          max="80"
          value={fontSize}
          onChange={(e) => setFontSize(parseInt(e.target.value))}
          className="w-full accent-blue-500"
        />
      </div>
      <div>
        <label className="text-sm text-gray-400 mb-1 block">Outline Width: {outlineWidth}px</label>
        <input
          type="range"
          min="0"
          max="8"
          value={outlineWidth}
          onChange={(e) => setOutlineWidth(parseInt(e.target.value))}
          className="w-full accent-blue-500"
        />
      </div>
      <div className="flex gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-sm text-gray-400">Font Color</label>
          <input
            type="color"
            value={fontColor}
            onChange={(e) => setFontColor(e.target.value)}
            className="h-9 w-16 rounded cursor-pointer bg-gray-800 border border-gray-700"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm text-gray-400">Outline</label>
          <input
            type="color"
            value={outlineColor}
            onChange={(e) => setOutlineColor(e.target.value)}
            className="h-9 w-16 rounded cursor-pointer bg-gray-800 border border-gray-700"
          />
        </div>
      </div>
      <Select
        label="Position"
        value={position}
        onValueChange={setPosition}
        options={POSITION_OPTIONS}
      />
      <Select
        label="Animation"
        value={animationType}
        onValueChange={setAnimationType}
        options={ANIMATION_OPTIONS}
      />
      {error && <p className="col-span-2 text-sm text-red-400">{error.message}</p>}
      <Button type="submit" loading={isPending} disabled={!name.trim()} className="col-span-2">
        Create Style
      </Button>
    </form>
  )
}

export default function SettingsPage() {
  const qc = useQueryClient()
  const [showNewStyleForm, setShowNewStyleForm] = useState(false)
  const [selectedStyleId, setSelectedStyleId] = useState<string | null>(null)

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  })

  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['config'],
    queryFn: fetchConfig,
  })

  const { data: captionStyles = [], isLoading: stylesLoading } = useQuery({
    queryKey: ['caption-styles'],
    queryFn: fetchCaptionStyles,
  })

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Settings" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto flex flex-col gap-6">

          {/* Health Status */}
          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-gray-300">System Health</h2>
            </CardHeader>
            <CardBody>
              {healthLoading ? (
                <Spinner />
              ) : health ? (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Status</span>
                    <Badge variant={health.status === 'ok' ? 'success' : 'error'}>
                      {health.status}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Version</span>
                    <span className="text-sm text-gray-300">{health.version}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">CUDA</span>
                    <Badge variant={health.cuda_available ? 'success' : 'default'}>
                      {health.cuda_available ? 'Available' : 'Not available'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">NVENC</span>
                    <Badge variant={health.nvenc_available ? 'success' : 'default'}>
                      {health.nvenc_available ? 'Available' : 'Not available'}
                    </Badge>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-red-400">Could not connect to backend at :8400</p>
              )}
            </CardBody>
          </Card>

          {/* Config */}
          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-gray-300">Configuration</h2>
            </CardHeader>
            <CardBody>
              {configLoading ? (
                <Spinner />
              ) : config ? (
                <div className="flex flex-col gap-2">
                  {Object.entries(config).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-sm text-gray-400">{key}</span>
                      <span className="text-sm text-gray-300 font-mono">{String(value)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No config available.</p>
              )}
            </CardBody>
          </Card>

          {/* Caption Styles */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-300">Caption Styles</h2>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setShowNewStyleForm((v) => !v)}
                >
                  {showNewStyleForm ? 'Cancel' : '+ New Style'}
                </Button>
              </div>
            </CardHeader>
            <CardBody className="flex flex-col gap-4">
              {showNewStyleForm && (
                <div className="border border-gray-700 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-300 mb-3">New Caption Style</h3>
                  <NewStyleForm
                    onCreated={() => {
                      setShowNewStyleForm(false)
                      void qc.invalidateQueries({ queryKey: ['caption-styles'] })
                    }}
                  />
                </div>
              )}
              <StylePicker
                styles={captionStyles}
                isLoading={stylesLoading}
                selectedId={selectedStyleId}
                onSelect={setSelectedStyleId}
              />
            </CardBody>
          </Card>

        </div>
      </div>
    </div>
  )
}
