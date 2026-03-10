"""
Heuristic emotional intensity scoring from transcript text.
No ML model required — fast text pattern analysis.

Signals scored:
  - Exclamation marks: +0.1 each (cap at 0.3)
  - ALL CAPS words: +0.15 each (cap at 0.3)
  - Question marks: +0.05 each (cap at 0.15)
  - Strong emotion words (anger, excitement, fear lists): +0.2
  - Laughter markers: +0.1
  - Negation + strong word (never, absolutely not): +0.15
  - Very short segments (<3 words): -0.1
  - Combined score clamped to [0.0, 1.0]
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Word lists ─────────────────────────────────────────────────────────────────

ANGER_WORDS = {
    "outrageous", "disgrace", "unacceptable", "terrible", "awful", "disgusting",
    "infuriating", "ridiculous", "shameful", "pathetic", "incompetent", "corrupt",
    "criminal", "failure", "disaster", "catastrophe", "inexcusable", "intolerable",
    "abysmal", "appalling", "atrocious", "deplorable", "despicable", "horrific",
    "offensive", "reprehensible", "scandalous", "vile", "wretched", "abomination",
    "betrayal", "traitor", "liar", "lied", "lying", "cheat", "cheating", "cheated",
    "fraud", "fraudulent", "stolen", "steal", "stealing", "theft",
}

EXCITEMENT_WORDS = {
    "amazing", "incredible", "fantastic", "unbelievable", "extraordinary", "phenomenal",
    "breathtaking", "spectacular", "magnificent", "outstanding", "exceptional",
    "brilliant", "remarkable", "astonishing", "astounding", "jaw-dropping", "epic",
    "legendary", "groundbreaking", "revolutionary", "game-changing", "monumental",
    "historic", "unprecedented", "sensational", "thrilling", "exhilarating",
    "electrifying", "explosive", "mind-blowing", "stunning", "superb", "terrific",
    "wonderful", "glorious", "triumphant", "victorious", "celebrating",
}

FEAR_WORDS = {
    "terrifying", "dangerous", "threat", "crisis", "disaster", "catastrophic",
    "devastating", "alarming", "frightening", "horrifying", "nightmare", "peril",
    "emergency", "catastrophe", "tragedy", "collapse", "breakdown", "meltdown",
    "chaos", "panic", "desperate", "dire", "grave", "severe", "critical", "urgent",
    "imminent", "inevitable", "irreversible", "existential", "fatal", "deadly",
    "lethal", "toxic", "hazardous", "volatile", "explosive",
}

LAUGHTER_MARKERS = {
    "haha", "hahaha", "hahahaha", "lol", "heh", "lmao", "lmfao", "hilarious",
    "funny", "laughing", "laughed", "giggling", "cracking up", "rofl",
    "ha ha", "he he", "hehe", "heehee", "chortle", "chuckle", "snicker",
}

NEGATION_WORDS = {"never", "absolutely", "completely", "totally", "entirely", "utterly"}

_ALL_EMOTION_WORDS = ANGER_WORDS | EXCITEMENT_WORDS | FEAR_WORDS


def _tokenize(text: str) -> list[str]:
    """Return lowercase word tokens from text."""
    return re.findall(r"[a-zA-Z']+", text.lower())


def score_emotion(segments: list[dict]) -> list[dict]:
    """
    Adds 'heuristic_emotion_score' (0.0-1.0) to each segment (modifies in place).

    Scoring signals (see module docstring for full list).
    """
    for seg in segments:
        text: str = seg.get("segment_text", "") or ""
        score = 0.0

        # Signal: exclamation marks (+0.1 each, cap 0.3)
        exclaim_count = text.count("!")
        score += min(0.3, exclaim_count * 0.1)

        # Signal: question marks (+0.05 each, cap 0.15)
        question_count = text.count("?")
        score += min(0.15, question_count * 0.05)

        # Signal: ALL CAPS words (+0.15 each, cap 0.3)
        words_in_text = text.split()
        caps_words = [
            w for w in words_in_text
            if len(w) >= 2 and w.isupper() and w.isalpha()
        ]
        score += min(0.3, len(caps_words) * 0.15)

        tokens = _tokenize(text)
        token_set = set(tokens)

        # Signal: strong emotion words (+0.2 for any match, not per-word)
        if token_set & _ALL_EMOTION_WORDS:
            score += 0.2

        # Signal: laughter markers (+0.1 for any match)
        # Check both tokenised and original text (handles "ha ha" multi-word)
        laughter_found = bool(token_set & LAUGHTER_MARKERS)
        if not laughter_found:
            text_lower = text.lower()
            laughter_found = any(marker in text_lower for marker in LAUGHTER_MARKERS)
        if laughter_found:
            score += 0.1

        # Signal: negation + strong emotion word (+0.15)
        negation_found = bool(token_set & NEGATION_WORDS)
        if negation_found and (token_set & _ALL_EMOTION_WORDS):
            score += 0.15

        # Penalty: very short segments (<3 words)
        if len(tokens) < 3:
            score -= 0.1

        # Clamp to [0.0, 1.0]
        seg["heuristic_emotion_score"] = round(max(0.0, min(1.0, score)), 4)

    return segments
