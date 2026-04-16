"""Embed command logic — independently testable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def run_embed(inference: Any, file: Path) -> np.ndarray:
    """Extract speaker embedding from an audio file.

    Returns a 1D numpy array (the embedding vector).
    """
    embedding = inference(str(file))
    # Ensure 1D
    if embedding.ndim > 1:
        embedding = embedding.squeeze()
    return embedding


def format_json(embedding: np.ndarray, file: Path) -> str:
    """Format embedding as JSON with metadata."""
    return json.dumps({
        "file": str(file),
        "dimension": len(embedding),
        "embedding": embedding.tolist(),
    }, indent=2)


def format_numpy(embedding: np.ndarray, output: Path) -> None:
    """Save embedding as .npy file."""
    np.save(str(output), embedding)
