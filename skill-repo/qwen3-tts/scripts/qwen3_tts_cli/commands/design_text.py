"""Logic for design text command — voice from natural language description."""

import numpy as np


def design_speech(
    model,
    *,
    text: str,
    description: str,
    language: str = "Auto",
) -> tuple[np.ndarray, int]:
    """Design a voice from a description and generate speech.

    Returns (audio_array, sample_rate).
    """
    if not text.strip():
        raise ValueError("Text must not be empty")
    if not description.strip():
        raise ValueError("Voice description must not be empty")

    wavs, sr = model.generate_voice_design(
        text,
        description,
        language=language,
    )
    return wavs[0], sr
