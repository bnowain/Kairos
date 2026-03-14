"""
Build intent-scoring prompts and parse LLM responses.

Scores transcript segments against a user-defined natural language intent
rather than fixed dimensions (virality, hook, etc.).
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

INTENT_SCORING_PROMPT = """You are scoring transcript segments against a specific search intent.

INTENT: {query_text}

{few_shot_section}

For each segment below, score it from 0.0 to 1.0 on:
- intent_relevance_score: How well does this segment match the stated intent?
  1.0 = perfect match, exactly what the user is looking for
  0.5 = tangentially related but not a strong match
  0.0 = completely irrelevant

Also provide:
- intent_score_reason: One sentence explaining your score

Return ONLY a JSON array, one object per segment, in the same order as input.
Each object must have: "segment_index", "intent_relevance_score", "intent_score_reason"

Segments:
{segments_json}
"""

BATCH_SIZE = 20
BATCH_SIZE_WITH_EXAMPLES = 15


def build_few_shot_section(
    intent_profile_id: Optional[str],
    db: Optional[Session],
    max_positive: int = 5,
    max_negative: int = 3,
) -> str:
    """Build few-shot calibration examples from intent profile feedback."""
    if not intent_profile_id or db is None:
        return ""

    from kairos.models import IntentExample

    positives = (
        db.query(IntentExample)
        .filter(
            IntentExample.intent_profile_id == intent_profile_id,
            IntentExample.example_rating == 1,
        )
        .order_by(IntentExample.example_original_score.desc())
        .limit(max_positive)
        .all()
    )

    # Negative examples sorted by original_score DESC — false positives are
    # the most valuable calibration signal
    negatives = (
        db.query(IntentExample)
        .filter(
            IntentExample.intent_profile_id == intent_profile_id,
            IntentExample.example_rating == -1,
        )
        .order_by(IntentExample.example_original_score.desc())
        .limit(max_negative)
        .all()
    )

    if not positives and not negatives:
        return ""

    lines = [
        "CALIBRATION EXAMPLES — Use these to understand what the user considers relevant:\n"
    ]

    if positives:
        lines.append("GOOD MATCHES (the user rated these highly for this intent):")
        for i, ex in enumerate(positives, 1):
            ctx = ""
            if ex.example_context:
                try:
                    c = json.loads(ex.example_context)
                    parts = []
                    if c.get("speaker"):
                        parts.append(f"Speaker: {c['speaker']}")
                    if c.get("video_title"):
                        parts.append(c["video_title"])
                    ctx = f" [{', '.join(parts)}]" if parts else ""
                except (json.JSONDecodeError, TypeError):
                    pass
            note = f' | User note: "{ex.example_note}"' if ex.example_note else ""
            text = ex.example_text[:200]
            lines.append(f'{i}.{ctx}\n   "{text}"\n   -> Score: {ex.example_original_score or "N/A"}{note}\n')

    if negatives:
        lines.append(
            "BAD MATCHES (the user rejected these — do NOT score similar content highly):"
        )
        for i, ex in enumerate(negatives, 1):
            note = f' | User note: "{ex.example_note}"' if ex.example_note else ""
            text = ex.example_text[:200]
            lines.append(f'{i}. "{text}"\n   -> Rejected{note}\n')

    return "\n".join(lines)


def build_scoring_prompt(
    query_text: str,
    batch: list[dict],
    intent_profile_id: Optional[str] = None,
    db: Optional[Session] = None,
    custom_system_prompt: Optional[str] = None,
) -> str:
    """Build the full scoring prompt for a batch of candidates."""
    few_shot = build_few_shot_section(intent_profile_id, db)

    segments_for_prompt = []
    for i, cand in enumerate(batch):
        entry = {
            "segment_index": i,
            "speaker": cand.get("candidate_speaker") or "unknown",
            "text": cand.get("candidate_text", ""),
        }
        if cand.get("candidate_video_title"):
            entry["video_title"] = cand["candidate_video_title"]
        if cand.get("candidate_video_date"):
            entry["date"] = cand["candidate_video_date"]
        if cand.get("candidate_start_ms") is not None:
            entry["start"] = f"{cand['candidate_start_ms'] / 1000:.1f}s"
            entry["end"] = f"{cand.get('candidate_end_ms', 0) / 1000:.1f}s"
        segments_for_prompt.append(entry)

    prompt_template = custom_system_prompt or INTENT_SCORING_PROMPT

    return prompt_template.format(
        query_text=query_text,
        few_shot_section=few_shot,
        segments_json=json.dumps(segments_for_prompt, indent=2),
    )


def parse_intent_scores(raw_text: str, batch_size: int) -> list[dict]:
    """
    Parse LLM response into intent scores.
    Returns list of {intent_relevance_score, intent_score_reason} dicts.
    """
    text = raw_text.strip()

    # Strip markdown code fences
    if "```" in text:
        lines = text.splitlines()
        cleaned = []
        for line in lines:
            if line.strip().startswith("```"):
                continue
            cleaned.append(line)
        text = "\n".join(cleaned).strip()

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        logger.warning("intent_scorer: no JSON array found in response")
        return [{"intent_relevance_score": 0.5, "intent_score_reason": ""} for _ in range(batch_size)]

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        logger.warning("intent_scorer: JSON parse error (%s)", exc)
        return [{"intent_relevance_score": 0.5, "intent_score_reason": ""} for _ in range(batch_size)]

    if not isinstance(parsed, list):
        return [{"intent_relevance_score": 0.5, "intent_score_reason": ""} for _ in range(batch_size)]

    results = []
    for i in range(batch_size):
        if i < len(parsed) and isinstance(parsed[i], dict):
            raw = parsed[i]
            score = raw.get("intent_relevance_score", 0.5)
            try:
                score = max(0.0, min(1.0, float(score)))
            except (TypeError, ValueError):
                score = 0.5
            results.append({
                "intent_relevance_score": score,
                "intent_score_reason": str(raw.get("intent_score_reason", ""))[:500],
            })
        else:
            results.append({"intent_relevance_score": 0.5, "intent_score_reason": ""})

    return results


def get_batch_size(has_examples: bool) -> int:
    """Return batch size based on whether few-shot examples are present."""
    return BATCH_SIZE_WITH_EXAMPLES if has_examples else BATCH_SIZE
