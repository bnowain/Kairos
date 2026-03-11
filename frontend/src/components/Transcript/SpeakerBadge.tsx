import { cn } from '../../utils/cn'

const SPEAKER_COLORS = [
  'bg-blue-900 text-blue-300',
  'bg-orange-900 text-orange-300',
  'bg-green-900 text-green-300',
  'bg-purple-900 text-purple-300',
  'bg-pink-900 text-pink-300',
  'bg-teal-900 text-teal-300',
  'bg-yellow-900 text-yellow-300',
  'bg-red-900 text-red-300',
]

export function getSpeakerColor(speaker: string | null): string {
  if (!speaker) return 'bg-gray-800 text-gray-400'
  // Extract number from SPEAKER_XX or use hash
  const match = speaker.match(/(\d+)$/)
  const idx = match ? parseInt(match[1], 10) : speaker.charCodeAt(0)
  return SPEAKER_COLORS[idx % SPEAKER_COLORS.length] ?? 'bg-gray-800 text-gray-400'
}

interface SpeakerBadgeProps {
  speaker: string | null
  className?: string
}

export function SpeakerBadge({ speaker, className }: SpeakerBadgeProps) {
  const colorClass = getSpeakerColor(speaker)
  return (
    <span
      className={cn('inline-flex items-center rounded px-2 py-0.5 text-xs font-medium shrink-0', colorClass, className)}
    >
      {speaker ?? 'Unknown'}
    </span>
  )
}
