import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Search, ThumbsUp, ThumbsDown, Import, ChevronDown, ChevronUp,
  AlertCircle, CheckCircle2, Loader2, Plus,
} from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Progress } from '../components/ui/Progress'
import { Spinner } from '../components/ui/Spinner'
import {
  createSmartQuery, getSmartQuery, getSmartQueryResults,
  rateCandidate, importCandidateAsClip, listSmartQueries,
  listIntentProfiles, createIntentProfile,
} from '../api/smartQuery'
import type { SmartQueryOut, QueryCandidateOut, IntentProfileOut } from '../api/smartQuery'

// ── Query poller ──────────────────────────────────────────────────────────────

function useQueryPoller(queryId: string | null) {
  const [query, setQuery] = useState<SmartQueryOut | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!queryId) { setQuery(null); return }

    const poll = async () => {
      try {
        const data = await getSmartQuery(queryId)
        setQuery(data)
        if (['done', 'error'].includes(data.query_status)) {
          if (intervalRef.current) clearInterval(intervalRef.current)
        }
      } catch { /* keep polling */ }
    }

    poll()
    intervalRef.current = setInterval(poll, 3000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [queryId])

  return query
}

// ── Score bar ─────────────────────────────────────────────────────────────────

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color =
    score >= 0.8 ? 'bg-green-500' :
    score >= 0.5 ? 'bg-yellow-500' :
    score >= 0.3 ? 'bg-orange-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-8">{pct}%</span>
    </div>
  )
}

// ── Candidate card ────────────────────────────────────────────────────────────

function CandidateCard({ candidate, onUpdate }: {
  candidate: QueryCandidateOut
  onUpdate: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [rating, setRating] = useState(candidate.candidate_user_rating)

  const rateMut = useMutation({
    mutationFn: (r: 1 | -1) => rateCandidate(candidate.candidate_id, r),
    onSuccess: (data) => { setRating(data.candidate_user_rating); onUpdate() },
  })

  const importMut = useMutation({
    mutationFn: () => importCandidateAsClip(candidate.candidate_id),
    onSuccess: onUpdate,
  })

  const score = candidate.intent_relevance_score ?? 0

  return (
    <div className={`rounded-lg border p-3 flex flex-col gap-2 transition-colors ${
      rating === 1 ? 'border-green-700/50 bg-green-900/10' :
      rating === -1 ? 'border-red-700/30 bg-red-900/5 opacity-60' :
      'border-gray-800 bg-gray-900/60'
    }`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {candidate.candidate_speaker && (
              <span className="text-xs font-medium text-blue-400">
                {candidate.candidate_speaker}
              </span>
            )}
            {candidate.candidate_video_title && (
              <span className="text-xs text-gray-500 truncate">
                {candidate.candidate_video_title}
              </span>
            )}
          </div>
          <p className={`text-sm text-gray-200 ${expanded ? '' : 'line-clamp-2'}`}>
            {candidate.candidate_text}
          </p>
          {candidate.candidate_text.length > 150 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-gray-500 hover:text-gray-300 mt-0.5 flex items-center gap-0.5"
            >
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {expanded ? 'Less' : 'More'}
            </button>
          )}
        </div>
        <ScoreBar score={score} />
      </div>

      {/* Reason */}
      {candidate.intent_score_reason && (
        <p className="text-xs text-gray-500 italic">{candidate.intent_score_reason}</p>
      )}

      {/* Meta */}
      <div className="flex items-center gap-3 text-[10px] text-gray-600">
        {candidate.candidate_video_date && <span>{candidate.candidate_video_date}</span>}
        {candidate.candidate_start_ms != null && (
          <span>{Math.round(candidate.candidate_start_ms / 1000)}s</span>
        )}
        {candidate.intent_scorer_model && <span>{candidate.intent_scorer_model}</span>}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1.5 mt-1">
        <button
          onClick={() => rateMut.mutate(1)}
          disabled={rateMut.isPending}
          className={`p-1.5 rounded transition-colors ${
            rating === 1 ? 'bg-green-600/20 text-green-400' : 'text-gray-500 hover:text-green-400 hover:bg-green-900/20'
          }`}
          title="Good match"
        >
          <ThumbsUp className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => rateMut.mutate(-1)}
          disabled={rateMut.isPending}
          className={`p-1.5 rounded transition-colors ${
            rating === -1 ? 'bg-red-600/20 text-red-400' : 'text-gray-500 hover:text-red-400 hover:bg-red-900/20'
          }`}
          title="Not relevant"
        >
          <ThumbsDown className="w-3.5 h-3.5" />
        </button>
        {candidate.candidate_origin === 'kairos' && !candidate.imported_as_clip_id && (
          <button
            onClick={() => importMut.mutate()}
            disabled={importMut.isPending}
            className="flex items-center gap-1 ml-2 px-2 py-1 rounded text-xs text-gray-400 hover:text-blue-400 hover:bg-blue-900/20 transition-colors"
          >
            <Import className="w-3.5 h-3.5" />
            Import as clip
          </button>
        )}
        {candidate.imported_as_clip_id && (
          <span className="flex items-center gap-1 ml-2 text-xs text-green-500">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Imported
          </span>
        )}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SmartQueryPage() {
  const queryClient = useQueryClient()
  const [queryText, setQueryText] = useState('')
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null)
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  const activeQuery = useQueryPoller(activeQueryId)

  const { data: profiles = [] } = useQuery({
    queryKey: ['intentProfiles'],
    queryFn: listIntentProfiles,
  })

  const { data: results = [], refetch: refetchResults } = useQuery({
    queryKey: ['smartQueryResults', activeQueryId],
    queryFn: () => activeQueryId ? getSmartQueryResults(activeQueryId, 0, 100) : Promise.resolve([]),
    enabled: !!activeQueryId && activeQuery?.query_status === 'done',
  })

  const { data: recentQueries = [] } = useQuery({
    queryKey: ['smartQueries'],
    queryFn: listSmartQueries,
    enabled: !activeQueryId,
  })

  const handleSubmit = async () => {
    if (!queryText.trim()) return
    setSubmitting(true)
    try {
      const result = await createSmartQuery({
        query_text: queryText.trim(),
        query_source: 'kairos',
        intent_profile_id: selectedProfile,
        filters: Object.keys(filters).length > 0 ? filters : null,
      })
      setActiveQueryId(result.query_id)
    } catch {
      // handle error
    }
    setSubmitting(false)
  }

  const handleBack = () => {
    setActiveQueryId(null)
    setQueryText('')
    setFilters({})
    queryClient.invalidateQueries({ queryKey: ['smartQueries'] })
  }

  const updateFilter = (key: string, value: string) => {
    if (value) {
      setFilters(f => ({ ...f, [key]: value }))
    } else {
      setFilters(f => {
        const next = { ...f }
        delete next[key]
        return next
      })
    }
  }

  // ── Results view ───────────────────────────────────────────────────────────
  if (activeQueryId) {
    const isDone = activeQuery?.query_status === 'done'
    const isError = activeQuery?.query_status === 'error'

    return (
      <div className="flex flex-col h-full overflow-hidden">
        <TopBar
          title="Smart Query"
          actions={
            <button
              onClick={handleBack}
              className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              New query
            </button>
          }
        />
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto p-4 md:p-6 flex flex-col gap-4">
            {/* Query text */}
            <div className="rounded-lg bg-gray-800/50 border border-gray-700 p-3">
              <p className="text-sm text-gray-300">"{activeQuery?.query_text ?? queryText}"</p>
            </div>

            {/* Progress */}
            {!isDone && !isError && (
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  <span className="text-sm text-gray-400">
                    {activeQuery?.query_stage_label ?? 'Starting…'}
                  </span>
                </div>
                <Progress value={activeQuery?.query_progress ?? 0} className="h-1.5" />
              </div>
            )}

            {/* Error */}
            {isError && activeQuery?.query_error_msg && (
              <div className="flex items-start gap-2 rounded-md bg-red-900/30 border border-red-700/50 p-3">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-xs text-red-300">{activeQuery.query_error_msg}</p>
              </div>
            )}

            {/* Results summary */}
            {isDone && (
              <p className="text-xs text-gray-500">
                {results.length} result{results.length !== 1 ? 's' : ''} found
                {activeQuery?.scorer_models?.[0] && ` — scored by ${activeQuery.scorer_models[0]}`}
              </p>
            )}

            {/* Result cards */}
            {isDone && results.map(c => (
              <CandidateCard
                key={c.candidate_id}
                candidate={c}
                onUpdate={() => refetchResults()}
              />
            ))}

            {isDone && results.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-8">
                No results matched your query.
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }

  // ── Query form ─────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Smart Query" />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-4 md:p-6 flex flex-col gap-6">

          {/* Query input */}
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
              What are you looking for?
            </h2>
            <textarea
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              placeholder="e.g. Moments where a speaker was combative or accusational toward staff..."
              rows={3}
              className="w-full rounded-lg border border-gray-700 bg-gray-800/50 px-4 py-3 text-sm text-gray-200 placeholder:text-gray-600 focus:border-blue-500 focus:outline-none resize-none"
            />
          </section>

          {/* Intent profile */}
          {profiles.length > 0 && (
            <section className="flex flex-col gap-2">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
                Intent Profile <span className="text-gray-600 font-normal">(optional)</span>
              </h2>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setSelectedProfile(null)}
                  className={`rounded-full px-3 py-1 text-xs border transition-colors ${
                    !selectedProfile
                      ? 'border-blue-500 bg-blue-600/10 text-blue-300'
                      : 'border-gray-700 text-gray-400 hover:border-gray-600'
                  }`}
                >
                  None
                </button>
                {profiles.map(p => (
                  <button
                    key={p.intent_profile_id}
                    onClick={() => setSelectedProfile(p.intent_profile_id)}
                    className={`rounded-full px-3 py-1 text-xs border transition-colors ${
                      selectedProfile === p.intent_profile_id
                        ? 'border-blue-500 bg-blue-600/10 text-blue-300'
                        : 'border-gray-700 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    {p.intent_name}
                    {p.intent_example_count > 0 && (
                      <span className="ml-1 text-gray-600">({p.intent_example_count})</span>
                    )}
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Filters toggle */}
          <section className="flex flex-col gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-300 transition-colors w-fit"
            >
              {showFilters ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              Filters
            </button>
            {showFilters && (
              <div className="grid grid-cols-2 gap-2">
                <Input
                  placeholder="Speaker name"
                  value={filters.speaker ?? ''}
                  onChange={e => updateFilter('speaker', e.target.value)}
                />
                <Input
                  placeholder="Channel"
                  value={filters.item_channel ?? ''}
                  onChange={e => updateFilter('item_channel', e.target.value)}
                />
                <Input
                  placeholder="Keyword"
                  value={filters.keyword ?? ''}
                  onChange={e => updateFilter('keyword', e.target.value)}
                />
                <Input
                  placeholder="After date (YYYY-MM-DD)"
                  value={filters.date_after ?? ''}
                  onChange={e => updateFilter('date_after', e.target.value)}
                />
              </div>
            )}
          </section>

          {/* Search button */}
          <Button
            onClick={handleSubmit}
            disabled={!queryText.trim() || submitting}
            className="w-full py-3 text-base font-semibold"
          >
            {submitting ? <Spinner size="sm" /> : (
              <>
                <Search className="w-4 h-4 mr-2" />
                Search
              </>
            )}
          </Button>

          {/* Recent queries */}
          {recentQueries.length > 0 && (
            <section className="flex flex-col gap-2">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
                Recent Queries
              </h2>
              {recentQueries.slice(0, 5).map(q => (
                <button
                  key={q.query_id}
                  onClick={() => {
                    setQueryText(q.query_text)
                    setActiveQueryId(q.query_id)
                  }}
                  className="text-left rounded-lg border border-gray-800 bg-gray-900/40 p-3 hover:border-gray-700 transition-colors"
                >
                  <p className="text-sm text-gray-300 line-clamp-1">{q.query_text}</p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-600">
                    <span className={
                      q.query_status === 'done' ? 'text-green-500' :
                      q.query_status === 'error' ? 'text-red-400' : 'text-gray-500'
                    }>
                      {q.query_status}
                    </span>
                    <span>{q.query_result_count} results</span>
                  </div>
                </button>
              ))}
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
