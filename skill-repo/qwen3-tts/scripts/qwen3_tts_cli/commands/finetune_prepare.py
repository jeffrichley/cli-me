"""Logic for finetune prepare command — validate and prepare training data."""

from pathlib import Path


def validate_audio_dir(audio_dir: str) -> dict:
    """Validate an audio directory has WAV files for training.

    Returns a dict with validation results.
    """
    path = Path(audio_dir)
    if not path.exists():
        raise FileNotFoundError(f"Audio directory not found: {audio_dir}")

    wav_files = sorted(path.glob("*.wav"))
    return {
        "audio_dir": str(path),
        "wav_count": len(wav_files),
        "valid": len(wav_files) > 0,
        "files": [f.name for f in wav_files],
    }
