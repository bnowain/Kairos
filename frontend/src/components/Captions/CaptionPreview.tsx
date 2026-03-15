interface CaptionPreviewProps {
  fontName: string
  fontSize: number
  fontColor: string
  outlineColor: string
  outlineWidth: number
  shadow: number
  position: string
}

export function CaptionPreview({
  fontName,
  fontSize,
  fontColor,
  outlineColor,
  outlineWidth,
  shadow,
  position,
}: CaptionPreviewProps) {
  const alignItems =
    position === 'top' ? 'flex-start' : position === 'middle' ? 'center' : 'flex-end'

  const scaledFontSize = Math.min(fontSize, 48) // cap for preview

  const textShadow = [
    outlineWidth > 0 ? `${outlineWidth}px ${outlineWidth}px 0 ${outlineColor}` : '',
    outlineWidth > 0 ? `-${outlineWidth}px -${outlineWidth}px 0 ${outlineColor}` : '',
    outlineWidth > 0 ? `${outlineWidth}px -${outlineWidth}px 0 ${outlineColor}` : '',
    outlineWidth > 0 ? `-${outlineWidth}px ${outlineWidth}px 0 ${outlineColor}` : '',
    shadow > 0 ? `${shadow * 2}px ${shadow * 2}px ${shadow * 3}px rgba(0,0,0,0.8)` : '',
  ]
    .filter(Boolean)
    .join(', ')

  return (
    <div
      className="aspect-video bg-gray-950 rounded-lg border border-gray-700 overflow-hidden flex px-4 py-6"
      style={{ alignItems, justifyContent: 'center' }}
    >
      <p
        className="text-center max-w-full break-words"
        style={{
          fontFamily: fontName,
          fontSize: `${scaledFontSize}px`,
          color: fontColor,
          textShadow: textShadow || undefined,
        }}
      >
        The quick brown fox jumps over the lazy dog
      </p>
    </div>
  )
}
