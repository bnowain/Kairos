#!/usr/bin/env python3
"""
push_query.py — Search Kairos transcription segments, score with LLM, push to UI.

Uses the same intent-scoring pipeline as the Smart Query orchestrator:
  1. Fetches segments from kairos.db (same filters as data_fetcher.py)
  2. Scores each batch through the configured LLM provider (same prompt as intent_scorer.py)
  3. POSTs scored results to Kairos /api/smart-query/push
  4. Results appear immediately in Smart Query UI for review

Usage from Claude Code CLI:

    # Basic search — uses configured LLM_PROVIDER for scoring
    python scripts/push_query.py "moments where the speaker gets defensive"

    # With filters
    python scripts/push_query.py "budget discussion" --speaker SPEAKER_01 --channel "City Council"

    # Use a specific provider for scoring
    python scripts/push_query.py "combative moments" --provider claude_cli

    # Skip LLM scoring (keyword-only, faster for testing)
    python scripts/push_query.py "zoning variance" --keyword-only

    # Programmatic usage (from Claude Code or any Python):
    from scripts.push_query import search_and_push
    result = search_and_push("combative moments", speaker="SPEAKER_00")
    print(result["query_id"])

The Kairos server must be running at localhost:8400.
"""

import argparse
import json
import logging
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Resolve paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "kairos.db"
KAIROS_URL = "http://localhost:8400"

# Add project root to path so we can import kairos modules
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="  %(message)s")
logger = logging.getLogger(__name__)


def _fetch_segments(
    speaker: str | None = None,
    channel: str | None = None,
    keyword: str | None = None,
    date_after: str | None = None,
    item_id: str | None = None,
    max_candidates: int = 100,
) -> list[dict]:
    """
    Fetch candidates from kairos.db using the same logic as
    kairos.services.smart_query.data_fetcher.fetch_kairos_candidates.
    """
    import sqlite3

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    sql = """
        SELECT
            s.segment_id,
            s.item_id,
            s.speaker_label,
            s.start_ms,
            s.end_ms,
            s.segment_text,
            m.item_title,
            m.published_at,
            m.original_url,
            m.item_channel
        FROM transcription_segments s
        JOIN media_items m ON s.item_id = m.item_id
        WHERE m.item_status = 'ready'
    """
    params: list = []

    if speaker:
        sql += " AND s.speaker_label LIKE ?"
        params.append(f"%{speaker}%")

    if channel:
        sql += " AND m.item_channel LIKE ?"
        params.append(f"%{channel}%")

    if keyword:
        sql += " AND s.segment_text LIKE ?"
        params.append(f"%{keyword}%")

    if date_after:
        sql += " AND m.published_at >= ?"
        params.append(date_after)

    if item_id:
        sql += " AND s.item_id = ?"
        params.append(item_id)

    sql += " ORDER BY m.published_at DESC, s.start_ms ASC"
    sql += f" LIMIT {max_candidates}"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    candidates = []
    for r in rows:
        candidates.append({
            "candidate_origin": "kairos",
            "candidate_item_id": r["item_id"],
            "candidate_segment_id": r["segment_id"],
            "candidate_speaker": r["speaker_label"],
            "candidate_text": r["segment_text"],
            "candidate_start_ms": r["start_ms"],
            "candidate_end_ms": r["end_ms"],
            "candidate_video_title": r["item_title"],
            "candidate_video_date": r["published_at"],
            "candidate_source_url": r["original_url"],
        })

    return candidates


def _keyword_score(text: str, query: str) -> tuple[float, str]:
    """Fallback keyword scoring (--keyword-only mode)."""
    query_words = set(re.findall(r'\w+', query.lower()))
    seg_words = set(re.findall(r'\w+', text.lower()))
    if not query_words:
        return 0.0, "empty query"
    matches = query_words & seg_words
    score = len(matches) / len(query_words)
    if query.lower() in text.lower():
        score = min(1.0, score + 0.3)
    reason = f"Matched {len(matches)}/{len(query_words)} keywords"
    if matches:
        reason += f": {', '.join(sorted(matches)[:5])}"
    return round(score, 3), reason


def _llm_score_batch(
    query_text: str,
    batch: list[dict],
    provider_name: str | None = None,
) -> list[dict]:
    """
    Score a batch using the same LLM prompt as the Smart Query orchestrator.
    Returns list of {intent_relevance_score, intent_score_reason}.
    """
    from kairos.services.smart_query.intent_scorer import (
        build_scoring_prompt, parse_intent_scores,
    )
    from kairos.services.llm_providers import get_provider, get_model_id

    call_fn, resolved_provider = get_provider(provider_name)
    model_id = get_model_id(provider_name)

    batch_dicts = [
        {
            "candidate_speaker": c.get("candidate_speaker"),
            "candidate_text": c.get("candidate_text", ""),
            "candidate_video_title": c.get("candidate_video_title"),
            "candidate_video_date": c.get("candidate_video_date"),
            "candidate_start_ms": c.get("candidate_start_ms"),
            "candidate_end_ms": c.get("candidate_end_ms"),
        }
        for c in batch
    ]

    prompt = build_scoring_prompt(
        query_text=query_text,
        batch=batch_dicts,
    )

    try:
        raw_text = call_fn(prompt)
        scores = parse_intent_scores(raw_text, len(batch))
    except Exception as exc:
        logger.warning("LLM scoring failed (%s): %s — falling back to 0.5", resolved_provider, exc)
        scores = [{"intent_relevance_score": 0.5, "intent_score_reason": f"Scoring error: {exc}"} for _ in batch]

    return scores


def _push_to_kairos(query_text: str, scored_candidates: list[dict], scorer_model: str) -> dict:
    """POST scored results to Kairos push endpoint."""
    payload = {
        "query_text": query_text,
        "scorer_model": scorer_model,
        "candidates": scored_candidates,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{KAIROS_URL}/api/smart-query/push",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        print(f"ERROR: Kairos API returned {exc.code}: {detail}", file=sys.stderr)
        return {"error": detail}
    except urllib.error.URLError as exc:
        print(f"ERROR: Cannot reach Kairos at {KAIROS_URL}: {exc.reason}", file=sys.stderr)
        print("Is the Kairos server running?", file=sys.stderr)
        return {"error": str(exc.reason)}


def search_and_push(
    query_text: str,
    speaker: str | None = None,
    channel: str | None = None,
    keyword: str | None = None,
    date_after: str | None = None,
    item_id: str | None = None,
    limit: int = 50,
    min_score: float = 0.1,
    provider: str | None = None,
    keyword_only: bool = False,
    batch_size: int = 20,
) -> dict:
    """
    Search segments, score with LLM (or keywords), push to Kairos Smart Query UI.
    Returns the API response (includes query_id for UI deep-link).
    """
    # Step 1: Fetch segments
    print(f"  Searching segments...")
    candidates = _fetch_segments(
        speaker=speaker,
        channel=channel,
        keyword=keyword,
        date_after=date_after,
        item_id=item_id,
        max_candidates=limit * 5,  # fetch more, trim after scoring
    )

    if not candidates:
        print("  No segments found matching criteria.", file=sys.stderr)
        return {"error": "no_segments"}

    print(f"  Found {len(candidates)} segments to score.")

    # Step 2: Score
    if keyword_only:
        scorer_model = "keyword_match"
        for c in candidates:
            score, reason = _keyword_score(c["candidate_text"], query_text)
            c["intent_relevance_score"] = score
            c["intent_score_reason"] = reason
        print(f"  Scored with keyword matching.")
    else:
        from kairos.services.llm_providers import get_model_id
        scorer_model = get_model_id(provider)
        print(f"  Scoring with LLM ({scorer_model})...")

        for batch_start in range(0, len(candidates), batch_size):
            batch = candidates[batch_start:batch_start + batch_size]
            scores = _llm_score_batch(query_text, batch, provider)

            for cand, score_data in zip(batch, scores):
                cand["intent_relevance_score"] = score_data["intent_relevance_score"]
                cand["intent_score_reason"] = score_data["intent_score_reason"]

            done = min(batch_start + batch_size, len(candidates))
            print(f"    Scored {done}/{len(candidates)}")

    # Step 3: Filter and sort
    scored = [c for c in candidates if (c.get("intent_relevance_score") or 0) >= min_score]
    scored.sort(key=lambda x: x.get("intent_relevance_score", 0), reverse=True)
    scored = scored[:limit]

    if not scored:
        print(f"  No segments scored above {min_score} threshold.", file=sys.stderr)
        return {"error": "no_matches"}

    # Step 4: Push to Kairos
    print(f"  Pushing {len(scored)} results to Kairos...")
    result = _push_to_kairos(query_text, scored, scorer_model)

    if "error" not in result:
        print(f"  Done!")
        print(f"  Query ID:  {result['query_id']}")
        print(f"  Results:   {result['query_result_count']}")
        print(f"  Review at: http://localhost:5173/smart-query")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Search Kairos segments, score with LLM, push to Smart Query UI",
    )
    parser.add_argument("query", help="What to search for (natural language)")
    parser.add_argument("--speaker", help="Filter by speaker label (substring match)")
    parser.add_argument("--channel", help="Filter by channel name (substring match)")
    parser.add_argument("--keyword", help="Pre-filter: only segments containing this keyword")
    parser.add_argument("--date-after", help="Only videos published after (YYYY-MM-DD)")
    parser.add_argument("--item-id", help="Restrict to a specific media item")
    parser.add_argument("--limit", type=int, default=50, help="Max results to push (default: 50)")
    parser.add_argument("--min-score", type=float, default=0.1, help="Min relevance score (default: 0.1)")
    parser.add_argument("--provider", help="LLM provider: ollama | claude_cli | mission_control")
    parser.add_argument("--keyword-only", action="store_true", help="Skip LLM, use keyword matching only")
    parser.add_argument("--batch-size", type=int, default=20, help="Segments per LLM call (default: 20)")
    args = parser.parse_args()

    search_and_push(
        query_text=args.query,
        speaker=args.speaker,
        channel=args.channel,
        keyword=args.keyword,
        date_after=args.date_after,
        item_id=args.item_id,
        limit=args.limit,
        min_score=args.min_score,
        provider=args.provider,
        keyword_only=args.keyword_only,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
