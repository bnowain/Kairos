import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../../api/client'

interface MCStatusResponse {
  available: boolean
  status: string
}

export function MCStatusPill() {
  const [available, setAvailable] = useState<boolean | null>(null)
  const [starting, setStarting] = useState(false)

  const checkStatus = useCallback(async () => {
    try {
      const data = await apiFetch<MCStatusResponse>('/api/mc/status')
      setAvailable(data.available)
    } catch {
      setAvailable(false)
    }
  }, [])

  // Poll every 15s, and on mount
  useEffect(() => {
    checkStatus()
    const id = setInterval(checkStatus, 15000)
    return () => clearInterval(id)
  }, [checkStatus])

  // When starting, poll more aggressively until it comes up
  useEffect(() => {
    if (!starting) return
    const id = setInterval(async () => {
      try {
        const data = await apiFetch<MCStatusResponse>('/api/mc/status')
        if (data.available) {
          setAvailable(true)
          setStarting(false)
        }
      } catch { /* keep polling */ }
    }, 2000)
    // Give up after 30s
    const timeout = setTimeout(() => { setStarting(false) }, 30000)
    return () => { clearInterval(id); clearTimeout(timeout) }
  }, [starting])

  const handleClick = async () => {
    if (available) return // already running, nothing to do
    setStarting(true)
    try {
      await apiFetch<{ started: boolean }>('/api/mc/start', { method: 'POST' })
    } catch {
      setStarting(false)
    }
  }

  const dotColor = available
    ? 'bg-green-500 shadow-green-500/50'
    : starting
      ? 'bg-yellow-500 shadow-yellow-500/50 animate-pulse'
      : 'bg-red-500 shadow-red-500/50'

  const label = available ? 'MC Online' : starting ? 'Starting...' : 'MC Offline'
  const clickable = !available && !starting

  return (
    <button
      onClick={handleClick}
      disabled={!clickable}
      title={
        available
          ? 'Mission Control is running'
          : starting
            ? 'Starting Mission Control...'
            : 'Click to start Mission Control'
      }
      className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-all ${
        clickable
          ? 'hover:bg-gray-700 cursor-pointer'
          : 'cursor-default'
      } ${
        available
          ? 'bg-green-900/20 text-green-400 border border-green-800/50'
          : starting
            ? 'bg-yellow-900/20 text-yellow-400 border border-yellow-800/50'
            : 'bg-red-900/20 text-red-400 border border-red-800/50'
      }`}
    >
      <span className={`h-2 w-2 rounded-full shadow-sm ${dotColor}`} />
      {label}
    </button>
  )
}
