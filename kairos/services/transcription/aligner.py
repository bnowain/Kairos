"""
Align word-level Whisper output with pyannote speaker turns.

Algorithm:
  For each word in the Whisper output:
    1. Find the speaker turn that overlaps most with [word.start, word.end]
    2. Assign that speaker label to the word
    3. Group consecutive words with the same speaker into a segment
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def align(
    whisper_segments: list[dict],   # output of transcriber.transcribe()
    diarization_turns: list[dict],  # output of diarizer.diarize()
) -> list[dict]:
    """
    Align word-level Whisper transcription with pyannote diarization turns.

    Args:
        whisper_segments:   List of segment dicts from transcriber.transcribe().
                            Each dict must have "words" (list of word dicts with
                            "start", "end", "word", "probability"), plus
                            "avg_logprob" and "no_speech_prob".
        diarization_turns:  List of turn dicts from diarizer.diarize().
                            Each dict has "start", "end", "speaker".

    Returns:
        List of merged aligned segments:
        [
            {
                "start":          float,
                "end":            float,
                "speaker":        str,    # "SPEAKER_00", "SPEAKER_01", etc.
                "text":           str,
                "words":          list,   # each word has "start", "end", "word",
                                          # "probability", "speaker"
                "avg_logprob":    float,
                "no_speech_prob": float,
            },
            ...
        ]
    """
    if not diarization_turns:
        logger.warning(
            "align: diarization_turns is empty — assigning all words to SPEAKER_00"
        )

    # ── Step 1: collect all words from all whisper segments ───────────────────
    # Each word also carries the segment-level confidence scores so we can
    # propagate them when we form new merged segments.
    all_words: list[dict] = []
    for seg in whisper_segments:
        seg_logprob     = seg.get("avg_logprob",    0.0)
        seg_no_speech   = seg.get("no_speech_prob", 0.0)
        for w in seg.get("words", []):
            all_words.append({
                "start":       w["start"],
                "end":         w["end"],
                "word":        w["word"],
                "probability": w["probability"],
                "speaker":     None,            # to be filled below
                # carry segment-level scores for averaging later
                "_avg_logprob":    seg_logprob,
                "_no_speech_prob": seg_no_speech,
            })

    if not all_words:
        return []

    # ── Step 2: assign a speaker to every word ────────────────────────────────
    prev_speaker = "SPEAKER_00"

    for word in all_words:
        w_start = word["start"]
        w_end   = word["end"]

        best_speaker  = None
        best_overlap  = 0.0

        for turn in diarization_turns:
            overlap = max(0.0, min(w_end, turn["end"]) - max(w_start, turn["start"]))
            if overlap > best_overlap:
                best_overlap  = overlap
                best_speaker  = turn["speaker"]

        if best_speaker is not None:
            word["speaker"] = best_speaker
            prev_speaker    = best_speaker
        else:
            # No overlapping turn — inherit previous word's speaker
            word["speaker"] = prev_speaker

    # ── Step 3: group consecutive same-speaker words into merged segments ─────
    aligned_segments: list[dict] = []
    current_words: list[dict] = []

    for word in all_words:
        if not current_words:
            current_words.append(word)
        elif word["speaker"] == current_words[-1]["speaker"]:
            current_words.append(word)
        else:
            # Speaker changed — flush current group
            aligned_segments.append(_merge_words(current_words))
            current_words = [word]

    # Flush last group
    if current_words:
        aligned_segments.append(_merge_words(current_words))

    logger.info(
        "align: %d whisper segments → %d aligned speaker segments",
        len(whisper_segments), len(aligned_segments),
    )

    return aligned_segments


def _merge_words(words: list[dict]) -> dict:
    """
    Merge a list of consecutive same-speaker words into one segment dict.

    text is formed by joining stripped words with a single space.
    avg_logprob and no_speech_prob are averaged from word-level segment scores.
    """
    speaker = words[0]["speaker"]
    start   = words[0]["start"]
    end     = words[-1]["end"]

    text = " ".join(w["word"].strip() for w in words if w["word"].strip())

    # Average confidence scores carried from the original whisper segments
    avg_logprob    = sum(w["_avg_logprob"]    for w in words) / len(words)
    no_speech_prob = sum(w["_no_speech_prob"] for w in words) / len(words)

    # Build clean word list (drop internal scoring fields)
    clean_words = [
        {
            "start":       w["start"],
            "end":         w["end"],
            "word":        w["word"],
            "probability": w["probability"],
            "speaker":     w["speaker"],
        }
        for w in words
    ]

    return {
        "start":          round(start, 3),
        "end":            round(end,   3),
        "speaker":        speaker,
        "text":           text,
        "words":          clean_words,
        "avg_logprob":    round(avg_logprob,    4),
        "no_speech_prob": round(no_speech_prob, 4),
    }
