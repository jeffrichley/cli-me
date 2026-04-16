"""Logic for generate text command — text-to-speech with built-in speakers."""

import numpy as np


def generate_speech(
    model,
    *,
    text: str,
    speaker: str,
    language: str = "Auto",
    instruct: str | None = None,
) -> tuple[np.ndarray, int]:
    """Generate speech from text using a built-in speaker.

    Returns (audio_array, sample_rate).
    """
    if not text.strip():
        raise ValueError("Text must not be empty")
    if not speaker.strip():
        raise ValueError("Speaker must not be empty")

    wavs, sr = model.generate_custom_voice(
        text,
        language,
        speaker,
        instruct=instruct,
    )
    return wavs[0], sr
