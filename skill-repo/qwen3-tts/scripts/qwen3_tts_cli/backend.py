"""Backend utilities for Qwen3-TTS CLI — model loading, device detection, audio I/O."""

import shutil
import subprocess
from pathlib import Path

import torch
import typer

# Model name mappings
CUSTOM_VOICE_MODELS = {
    "1.7b": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "0.6b": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
}

BASE_MODELS = {
    "1.7b": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "0.6b": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
}

# Cached model instance
_model_cache: dict = {}


def detect_device(force: str | None = None) -> str:
    """Auto-detect best available device. Returns 'cuda', 'mps', or 'cpu'."""
    if force:
        return force
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    typer.echo("WARNING: No GPU detected. Using CPU (will be slow).", err=True)
    return "cpu"


def model_name_from_size(size: str) -> str:
    """Return the HuggingFace model name for a CustomVoice model size."""
    if size not in CUSTOM_VOICE_MODELS:
        valid = ", ".join(sorted(CUSTOM_VOICE_MODELS))
        raise ValueError(f"Unknown model size '{size}'. Valid sizes: {valid}")
    return CUSTOM_VOICE_MODELS[size]


def base_model_name_from_size(size: str) -> str:
    """Return the HuggingFace model name for a Base model size (for fine-tuning/cloning)."""
    if size not in BASE_MODELS:
        valid = ", ".join(sorted(BASE_MODELS))
        raise ValueError(f"Unknown model size '{size}'. Valid sizes: {valid}")
    return BASE_MODELS[size]


def load_model(model_size: str = "1.7b", device: str | None = None):
    """Load a Qwen3-TTS CustomVoice model with caching.

    Returns the loaded model instance. Caches by (model_size, device) so
    subsequent calls with the same args return the same instance.
    """
    device = detect_device(device)
    cache_key = (model_size, device)
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    from qwen_tts import Qwen3TTSModel

    model_name = model_name_from_size(model_size)
    dtype = torch.bfloat16 if device != "cpu" else torch.float32

    model = Qwen3TTSModel.from_pretrained(
        model_name,
        device_map=f"{device}:0" if device == "cuda" else device,
        dtype=dtype,
    )
    _model_cache[cache_key] = model
    return model


def save_audio(
    audio_data,
    sample_rate: int,
    path: str,
    format: str = "wav",
) -> Path:
    """Save audio data to a file. Converts format via ffmpeg if not WAV."""
    import soundfile as sf

    output_path = Path(path)

    if format == "wav":
        sf.write(str(output_path), audio_data, sample_rate)
    else:
        # Write WAV to temp, convert via ffmpeg
        tmp_wav = output_path.with_suffix(".tmp.wav")
        sf.write(str(tmp_wav), audio_data, sample_rate)

        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            tmp_wav.unlink()
            typer.echo(
                f"ERROR: ffmpeg not found. Install ffmpeg to convert to {format}.\n"
                f"Or use --format wav (the default).",
                err=True,
            )
            raise typer.Exit(code=1)

        subprocess.run(
            [ffmpeg, "-y", "-i", str(tmp_wav), str(output_path)],
            check=True,
            capture_output=True,
        )
        tmp_wav.unlink()

    return output_path
