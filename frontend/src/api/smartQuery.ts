import { apiFetch } from './client'

export interface SmartQueryIn {
  query_text: string
  query_source?: string
  intent_profile_id?: string | null
  filters?: Record<string, string> | null
  scorer_models?: string[]
  max_candidates?: number
}

export interface SmartQueryOut {
  query_id: string
  query_text: string
  query_source: string
  query_status: string
  query_progress: number
  query_stage_label: string | null
  intent_profile_id: string | null
  scorer_models: string[] | null
  query_result_count: number
  query_error_msg: string | null
  created_at: string
  updated_at: string
}

export interface QueryCandidateOut {
  candidate_id: string
  query_id: string
  candidate_origin: string
  candidate_item_id: string | null
  candidate_segment_id: string | null
  candidate_speaker: string | null
  candidate_text: string
  candidate_start_ms: number | null
  candidate_end_ms: number | null
  candidate_video_title: string | null
  candidate_video_date: string | null
  candidate_source_url: string | null
  intent_relevance_score: number | null
  intent_score_reason: string | null
  intent_scorer_model: string | null
  candidate_user_rating: number | null
  candidate_rating_note: string | null
  imported_as_clip_id: string | null
  created_at: string
}

export interface IntentProfileOut {
  intent_profile_id: string
  intent_name: string
  intent_description: string | null
  intent_system_prompt: string | null
  intent_example_count: number
  created_at: string
  updated_at: string
}

export function createSmartQuery(req: SmartQueryIn): Promise<SmartQueryOut> {
  return apiFetch('/api/smart-query', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function getSmartQuery(queryId: string): Promise<SmartQueryOut> {
  return apiFetch(`/api/smart-query/${queryId}`)
}

export function listSmartQueries(): Promise<SmartQueryOut[]> {
  return apiFetch('/api/smart-query')
}

export function getSmartQueryResults(
  queryId: string,
  minScore = 0,
  limit = 50,
): Promise<QueryCandidateOut[]> {
  return apiFetch(
    `/api/smart-query/${queryId}/results?min_score=${minScore}&limit=${limit}`,
  )
}

export function rateCandidate(
  candidateId: string,
  rating: 1 | -1,
  note?: string,
): Promise<QueryCandidateOut> {
  return apiFetch(`/api/smart-query/candidates/${candidateId}/rate`, {
    method: 'POST',
    body: JSON.stringify({ rating, note, save_as_example: true }),
  })
}

export function importCandidateAsClip(
  candidateId: string,
): Promise<{ clip_id: string; already_imported: boolean }> {
  return apiFetch(`/api/smart-query/candidates/${candidateId}/import`, {
    method: 'POST',
  })
}

export function listIntentProfiles(): Promise<IntentProfileOut[]> {
  return apiFetch('/api/intent-profiles')
}

export function createIntentProfile(
  name: string,
  description?: string,
): Promise<IntentProfileOut> {
  return apiFetch('/api/intent-profiles', {
    method: 'POST',
    body: JSON.stringify({ intent_name: name, intent_description: description }),
  })
}
