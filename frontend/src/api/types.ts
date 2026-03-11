export interface MediaItem {
  item_id: string
  platform: string
  platform_video_id: string | null
  item_title: string | null
  item_channel: string | null
  item_description: string | null
  published_at: string | null
  duration_seconds: number | null
  original_url: string | null
  file_path: string | null
  audio_path: string | null
  thumb_path: string | null
  item_status: 'queued' | 'downloading' | 'downloaded' | 'ingesting' | 'ready' | 'error'
  error_msg: string | null
  has_captions: number
  caption_source: string | null
  created_at: string
  updated_at: string
  // Optional fields returned by detail endpoint or analysis
  virality_score?: number | null
  transcription_job_status?: string | null
  segment_count?: number
  clip_count?: number
}

export interface TranscriptionSegment {
  segment_id: string
  item_id: string
  speaker_label: string | null
  start_ms: number
  end_ms: number
  segment_text: string
  word_timestamps: string | null
  avg_logprob: number | null
  no_speech_prob: number | null
}

export interface TranscriptionJob {
  job_id: string
  item_id: string
  job_status: 'queued' | 'running' | 'done' | 'error'
  model_used: string | null
  language: string | null
  diarize: boolean
  error_msg: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface AnalysisScore {
  score_id: string
  item_id: string
  segment_id: string | null
  score_type: string
  score_value: number
  score_reason: string | null
  created_at: string
}

export interface AnalysisHighlight {
  segment_id: string
  segment_text: string
  start_ms: number
  end_ms: number
  speaker_label: string | null
  composite_score: number
  scores: Record<string, number>
}

export interface Clip {
  clip_id: string
  item_id: string
  clip_title: string | null
  start_ms: number
  end_ms: number
  duration_ms: number
  clip_file_path: string | null
  clip_thumb_path: string | null
  virality_score: number | null
  clip_status: 'pending' | 'extracting' | 'ready' | 'error'
  clip_source: 'ai' | 'manual'
  speaker_label: string | null
  clip_transcript: string | null
  error_msg: string | null
  created_at: string
  updated_at: string
}

export interface Timeline {
  timeline_id: string
  timeline_name: string
  story_template: string | null
  aspect_ratio: string
  target_duration_ms: number | null
  timeline_status: string
  element_count: number
  clip_count: number
  elements: TimelineElement[]
  created_at: string
  updated_at: string
}

export interface TimelineElement {
  element_id: string
  timeline_id: string
  element_type: 'clip' | 'transition' | 'title_card' | 'overlay'
  position: number
  start_ms: number
  duration_ms: number
  clip_id: string | null
  element_params: string | null
  created_at: string
}

export interface RenderJob {
  render_id: string
  timeline_id: string
  render_quality: 'preview' | 'final'
  output_path: string | null
  encoder: string | null
  render_status: 'queued' | 'running' | 'done' | 'error'
  render_params: string | null
  error_msg: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface StoryTemplate {
  template_id: string
  template_name: string
  description: string
  pacing: string
  target_duration_ms: number
  aspect_ratio_default: string
  slots?: TemplateSlot[]
}

export interface TemplateSlot {
  slot_id: string
  slot_label: string
  position: number
  required: boolean
  max_clips: number
  score_signals: string[]
  max_duration_ms: number
}

export interface CaptionStyle {
  style_id: string
  style_name: string
  platform_preset: string | null
  font_name: string
  font_size: number
  font_color: string
  outline_color: string
  outline_width: number
  shadow: number
  animation_type: string | null
  position: string
  created_at: string
}

export interface HealthStatus {
  status: string
  version: string
  cuda_available: boolean
  nvenc_available: boolean
}

export interface Config {
  port: number
  whisper_model: string
  ollama_host: string
  [key: string]: unknown
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
