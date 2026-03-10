"""
Sentence embedding-based topic segmentation.
Groups transcript segments into coherent topic blocks using cosine similarity.

Model: all-MiniLM-L6-v2 (fast, 384-dim, good for short text segments)
Loaded once and cached at module level.
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Module-level model cache — loaded lazily on first use
_model = None
_model_name = "all-MiniLM-L6-v2"


def _get_model():
    """Load (or return cached) SentenceTransformer model."""
    global _model
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer
        from kairos.config import CUDA_AVAILABLE

        device = "cuda" if CUDA_AVAILABLE else "cpu"
        logger.info("embedder: loading %s on %s", _model_name, device)
        _model = SentenceTransformer(_model_name, device=device)
        logger.info("embedder: model loaded")
    except ImportError:
        logger.warning("embedder: sentence-transformers not installed — embeddings disabled")
        _model = None
    except Exception as exc:
        logger.warning("embedder: failed to load model (%s) — embeddings disabled", exc)
        _model = None

    return _model


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two unit-normalised vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def embed_segments(segments: list[dict]) -> list[dict]:
    """
    Add embedding vectors to segments.
    Returns the same list with an 'embedding' key (numpy array) added to each segment.
    If the model is unavailable, 'embedding' is set to None for all segments.
    """
    if not segments:
        return segments

    model = _get_model()
    if model is None:
        for seg in segments:
            seg["embedding"] = None
        return segments

    texts = [seg.get("segment_text", "") or "" for seg in segments]

    try:
        embeddings = model.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        for seg, emb in zip(segments, embeddings):
            seg["embedding"] = emb
    except Exception as exc:
        logger.warning("embedder: encode failed (%s) — setting embeddings to None", exc)
        for seg in segments:
            seg["embedding"] = None

    return segments


def find_topic_boundaries(
    segments_with_embeddings: list[dict],
    threshold: float = 0.3,
) -> list[int]:
    """
    Find indices where topic changes significantly.

    Uses cosine similarity between adjacent segments.
    Returns list of segment indices that start a new topic block.
    Index 0 is always included (first block).
    Threshold: lower value = more boundaries detected.
    """
    if len(segments_with_embeddings) < 2:
        return [0] if segments_with_embeddings else []

    boundaries = [0]  # First segment always starts a block

    for i in range(1, len(segments_with_embeddings)):
        prev_emb = segments_with_embeddings[i - 1].get("embedding")
        curr_emb = segments_with_embeddings[i].get("embedding")

        if prev_emb is None or curr_emb is None:
            # No embeddings — can't detect boundary, skip
            continue

        sim = _cosine_sim(prev_emb, curr_emb)
        # Low similarity means topic change
        if sim < (1.0 - threshold):
            boundaries.append(i)

    return boundaries


def score_topic_coherence(segments: list[dict]) -> list[dict]:
    """
    For each segment, compute how central it is to its topic block.
    Adds 'topic_coherence_score' (0.0-1.0) to each segment.

    High coherence = representative of the topic; good for highlights.
    If embeddings are unavailable, defaults to 0.5 for all segments.
    """
    if not segments:
        return segments

    # Ensure embeddings exist
    has_embeddings = any(seg.get("embedding") is not None for seg in segments)
    if not has_embeddings:
        segments = embed_segments(segments)
        has_embeddings = any(seg.get("embedding") is not None for seg in segments)

    if not has_embeddings:
        for seg in segments:
            seg["topic_coherence_score"] = 0.5
        return segments

    boundaries = find_topic_boundaries(segments)

    # Build topic blocks: list of (start_idx, end_idx_exclusive)
    blocks = []
    for b_i, start in enumerate(boundaries):
        end = boundaries[b_i + 1] if b_i + 1 < len(boundaries) else len(segments)
        blocks.append((start, end))

    for start, end in blocks:
        block_segs = segments[start:end]
        block_embs = [s.get("embedding") for s in block_segs if s.get("embedding") is not None]

        if not block_embs:
            for seg in block_segs:
                seg["topic_coherence_score"] = 0.5
            continue

        # Compute centroid of block embeddings
        centroid = np.mean(np.stack(block_embs), axis=0)

        for seg in block_segs:
            emb = seg.get("embedding")
            if emb is not None:
                sim = _cosine_sim(emb, centroid)
                # Normalise: similarity is in [-1, 1], shift to [0, 1]
                score = max(0.0, min(1.0, (sim + 1.0) / 2.0))
                seg["topic_coherence_score"] = score
            else:
                seg["topic_coherence_score"] = 0.5

    return segments
