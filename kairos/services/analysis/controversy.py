"""
Controversy and rhetorical emphasis detection from transcript text.
Pattern-based — no LLM required.

Signals:
  - Direct contradiction patterns: +0.2
  - Strong claim patterns: +0.15
  - Political/charged terms: +0.1 each (cap 0.3)
  - Rhetorical questions: +0.1
  - Named entity + strong verb ("X said/did/claimed"): +0.15
  - Combined score clamped to [0.0, 1.0]
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Pattern lists ──────────────────────────────────────────────────────────────

CONTRADICTION_PHRASES = [
    "actually", "that's not true", "thats not true", "that is not true",
    "that's wrong", "thats wrong", "that is wrong", "incorrect", "false",
    "not correct", "you're wrong", "youre wrong", "he's wrong", "she's wrong",
    "they're wrong", "misinformation", "disinformation", "debunked", "fact check",
    "the truth is", "in reality", "contrary to", "despite claims", "despite what",
    "not accurate", "completely false", "simply not true",
]

CLAIM_PHRASES = [
    "i'm telling you", "im telling you", "i am telling you",
    "the truth is", "let me be clear", "let me be very clear",
    "the fact is", "the facts are", "make no mistake", "i can tell you",
    "what i'm saying is", "what im saying is", "what i am saying is",
    "i guarantee", "i promise you", "i assure you", "trust me",
    "you need to understand", "you have to understand", "here's what happened",
    "heres what happened", "here is what happened", "the reality is",
    "bottom line", "at the end of the day",
]

POLITICAL_TERMS = {
    "corrupt", "corruption", "scandal", "cover-up", "coverup", "lie", "lied",
    "lying", "fraud", "illegal", "criminal", "accountability", "resign",
    "impeach", "impeachment", "investigation", "coverup", "bribe", "bribery",
    "conspiracy", "rigged", "stolen", "unconstitutional", "abuse", "misconduct",
    "negligence", "incompetent", "incompetence", "failure", "failed", "betrayal",
    "betrayed", "traitor", "treason", "treasonous", "censorship", "suppressed",
    "suppression", "silenced", "banned", "propaganda", "narrative", "agenda",
    "manipulation", "manipulated", "controlled", "weaponized", "radical",
    "extremist", "extremism", "authoritarian", "fascist", "fascism",
}

# Strong verbs that often follow named entities in controversial statements
STRONG_VERBS = {
    "said", "claimed", "admitted", "confessed", "denied", "insisted",
    "alleged", "accused", "charged", "blamed", "criticised", "criticized",
    "condemned", "slammed", "attacked", "defended", "refused", "rejected",
    "contradicted", "reversed", "flip-flopped", "lied", "misled", "deceived",
    "manipulated", "covered", "buried", "ignored", "dismissed", "downplayed",
}

# Rhetorical question starters
RHETORICAL_STARTERS = [
    r"how can (you|we|they|anyone|he|she|it)",
    r"why would (you|we|they|anyone|he|she|it)",
    r"why did (you|we|they|he|she|it)",
    r"why (is|are|was|were) (you|we|they|he|she|it|this|that)",
    r"who (do|does|did) (you|we|they|he|she|it) think",
    r"what (is|was|were) (he|she|they|you|we) thinking",
    r"doesn't (anyone|somebody|he|she|it|this)",
    r"can('t| not) (you|we|they|he|she|anyone)",
    r"are (you|we|they) serious",
    r"is (this|that|he|she|it) serious",
]

_RHETORICAL_PATTERNS = [re.compile(p, re.IGNORECASE) for p in RHETORICAL_STARTERS]

# Named entity detector: 2+ consecutive capitalised words (e.g., "John Smith", "City Council")
_NAMED_ENTITY_RE = re.compile(r"(?:[A-Z][a-z]+\s+){1,3}[A-Z][a-z]+")


def _normalise(text: str) -> str:
    """Collapse multiple spaces and lowercase for substring search."""
    return " ".join(text.lower().split())


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", text.lower()))


def score_controversy(segments: list[dict]) -> list[dict]:
    """
    Adds 'heuristic_controversy_score' (0.0-1.0) to each segment (modifies in place).
    """
    for seg in segments:
        text: str = seg.get("segment_text", "") or ""
        score = 0.0
        norm_text = _normalise(text)
        tokens = _tokenize(text)

        # Signal: direct contradiction phrases (+0.2 for any match)
        for phrase in CONTRADICTION_PHRASES:
            if phrase in norm_text:
                score += 0.2
                break

        # Signal: strong claim phrases (+0.15 for any match)
        for phrase in CLAIM_PHRASES:
            if phrase in norm_text:
                score += 0.15
                break

        # Signal: political/charged terms (+0.1 each, cap 0.3)
        political_hits = tokens & POLITICAL_TERMS
        score += min(0.3, len(political_hits) * 0.1)

        # Signal: rhetorical questions (+0.1 for any match)
        for pattern in _RHETORICAL_PATTERNS:
            if pattern.search(text):
                score += 0.1
                break

        # Signal: named entity + strong verb (+0.15)
        named_entities = _NAMED_ENTITY_RE.findall(text)
        if named_entities and (tokens & STRONG_VERBS):
            score += 0.15

        # Clamp to [0.0, 1.0]
        seg["heuristic_controversy_score"] = round(max(0.0, min(1.0, score)), 4)

    return segments
