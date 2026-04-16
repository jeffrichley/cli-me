"""Logic for finetune generate command — generate from a fine-tuned model."""

import numpy as np


def generate_from_finetuned(
    model,
    *,
    text: str,
    language: str = "Auto",
    instruct: str | None = None,
) -> tuple[np.ndarray, int]:
    """Generate speech from a fine-tuned model.

    Fine-tuned models are single-speaker, so no speaker parameter.
    Returns (audio_array, sample_rate).
    """
    if not text.strip():
        raise ValueError("Text must not be empty")

    wavs, sr = model.generate_custom_voice(
        text,
        "custom_speaker",
        language=language,
        instruct=instruct,
    )
    return wavs[0], sr
