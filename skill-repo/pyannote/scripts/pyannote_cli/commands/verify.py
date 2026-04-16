"""Verify command logic — independently testable."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def extract_embedding(inference: Any, file: Path) -> np.ndarray:
    """Extract a speaker embedding from an audio file."""
    embedding = inference(str(file))
    # Normalize
    if isinstance(embedding, np.ndarray):
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
    return embedding


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a_flat = a.flatten()
    b_flat = b.flatten()
    dot = np.dot(a_flat, b_flat)
    norm_a = np.linalg.norm(a_flat)
    norm_b = np.linalg.norm(b_flat)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def verify_speakers(
    inference: Any,
    file_a: Path,
    file_b: Path,
    threshold: float = 0.7,
) -> dict:
    """Compare two audio files and determine if same speaker.

    Returns dict with score, same_speaker, and threshold.
    """
    emb_a = extract_embedding(inference, file_a)
    emb_b = extract_embedding(inference, file_b)
    score = cosine_similarity(emb_a, emb_b)
    return {
        "score": round(score, 4),
        "same_speaker": score >= threshold,
        "threshold": threshold,
    }
