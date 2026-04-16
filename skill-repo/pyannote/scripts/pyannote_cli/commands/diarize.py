"""Diarize command logic — independently testable."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def run_diarize(
    pipeline: Any,
    file: Path,
    num_speakers: int | None = None,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> Any:
    """Run speaker diarization on an audio file.

    Returns a DiarizeOutput (or Annotation for legacy pipelines).
    """
    kwargs = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    if min_speakers is not None:
        kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        kwargs["max_speakers"] = max_speakers

    return pipeline(str(file), **kwargs)


def format_rttm(output: Any, filename: str = "audio") -> str:
    """Format diarization output as RTTM string."""
    lines = []
    annotation = output.speaker_diarization if hasattr(output, "speaker_diarization") else output
    for segment, _, label in annotation.itertracks(yield_label=True):
        start = segment.start
        duration = segment.end - segment.start
        lines.append(
            f"SPEAKER {filename} 1 {start:.3f} {duration:.3f} <NA> <NA> {label} <NA> <NA>"
        )
    return "\n".join(lines)


def format_json(output: Any) -> str:
    """Format diarization output as JSON string."""
    import json

    if hasattr(output, "serialize"):
        return json.dumps(output.serialize(), indent=2)

    # Fallback for plain Annotation
    entries = []
    for segment, _, label in output.itertracks(yield_label=True):
        entries.append({
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "speaker": label,
        })
    return json.dumps({"diarization": entries}, indent=2)


def format_txt(output: Any) -> str:
    """Format diarization output as human-readable text."""
    lines = []
    annotation = output.speaker_diarization if hasattr(output, "speaker_diarization") else output
    for segment, _, label in annotation.itertracks(yield_label=True):
        start_m, start_s = divmod(segment.start, 60)
        end_m, end_s = divmod(segment.end, 60)
        lines.append(f"[{int(start_m):02d}:{start_s:05.2f} --> {int(end_m):02d}:{end_s:05.2f}] {label}")
    return "\n".join(lines)
