import { apiFetch } from './client'
import type { StoryTemplate, Timeline, TimelineElement } from './types'

export function fetchTemplates(): Promise<StoryTemplate[]> {
  return apiFetch<StoryTemplate[]>('/api/stories/templates')
}

export function fetchTemplate(templateId: string): Promise<StoryTemplate> {
  return apiFetch<StoryTemplate>(`/api/stories/templates/${templateId}`)
}

export interface GenerateStoryParams {
  template_id: string
  item_ids: string[]
  story_name?: string
  aspect_ratio?: string
  pacing_override?: string
  min_score?: number
}

export function generateStory(params: GenerateStoryParams): Promise<Timeline> {
  return apiFetch<Timeline>('/api/stories/generate', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export function fetchTimelines(): Promise<Timeline[]> {
  return apiFetch<Timeline[]>('/api/timelines')
}

export function fetchTimeline(timelineId: string): Promise<Timeline> {
  return apiFetch<Timeline>(`/api/timelines/${timelineId}`)
}

export function updateTimelineElement(
  timelineId: string,
  elementId: string,
  params: Partial<TimelineElement>,
): Promise<TimelineElement> {
  return apiFetch<TimelineElement>(`/api/timelines/${timelineId}/elements/${elementId}`, {
    method: 'PATCH',
    body: JSON.stringify(params),
  })
}

export function reorderElements(
  timelineId: string,
  elementIds: string[],
): Promise<Timeline> {
  return apiFetch<Timeline>(`/api/timelines/${timelineId}/reorder`, {
    method: 'POST',
    body: JSON.stringify({ element_ids: elementIds }),
  })
}

export function addTitleCard(
  timelineId: string,
  text: string,
  position?: number,
): Promise<TimelineElement> {
  return apiFetch<TimelineElement>(`/api/timelines/${timelineId}/elements`, {
    method: 'POST',
    body: JSON.stringify({ element_type: 'title_card', text, position }),
  })
}

export function deleteElement(timelineId: string, elementId: string): Promise<{ status: string }> {
  return apiFetch(`/api/timelines/${timelineId}/elements/${elementId}`, { method: 'DELETE' })
}
