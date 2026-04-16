"""Logic for clone text command — voice cloning from reference audio."""

from pathlib import Path

import numpy as np


def clone_speech(
    model,
    *,
    text: str,
    reference: str,
    ref_text: str,
    language: str = "Auto",
) -> tuple[np.ndarray, int]:
    """Clone a voice from reference audio and generate speech.

    Returns (audio_array, sample_rate).
    """
    if not text.strip():
        raise ValueError("Text must not be empty")
    if not ref_text.strip():
        raise ValueError("Reference text must not be empty")

    ref_path = Path(reference)
    if not ref_path.exists():
        raise FileNotFoundError(f"Reference audio file not found: {reference}")

    wavs, sr = model.generate_voice_clone(
        text=text,
        language=language,
        ref_audio=str(ref_path),
        ref_text=ref_text,
        non_streaming_mode=True,
    )
    return wavs[0], sr
