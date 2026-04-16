"""VAD command logic — independently testable."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def run_vad(pipeline: Any, file: Path) -> Any:
    """Run voice activity detection using the diarization pipeline.

    Runs speaker diarization and collapses all speaker labels into "SPEECH"
    regions. This works around pyannote/voice-activity-detection being
    incompatible with pyannote.audio v4.x.

    Returns an Annotation with "SPEECH" labels.
    """
    output = pipeline(str(file))
    diarization = output.speaker_diarization if hasattr(output, "speaker_diarization") else output
    return collapse_to_speech(diarization)


def collapse_to_speech(annotation: Any) -> Any:
    """Collapse all speaker labels in an annotation into 'SPEECH' labels."""
    from pyannote.core import Annotation

    vad = Annotation()
    for segment, _, _ in annotation.itertracks(yield_label=True):
        vad[segment] = "SPEECH"
    return vad.support()


def format_rttm(annotation: Any, filename: str = "audio") -> str:
    """Format VAD output as RTTM."""
    lines = []
    for segment, _, label in annotation.itertracks(yield_label=True):
        start = segment.start
        duration = segment.end - segment.start
        lines.append(
            f"SPEAKER {filename} 1 {start:.3f} {duration:.3f} <NA> <NA> {label} <NA> <NA>"
        )
    return "\n".join(lines)


def format_json(annotation: Any) -> str:
    """Format VAD output as JSON."""
    import json

    entries = []
    for segment, _, label in annotation.itertracks(yield_label=True):
        entries.append({
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "label": label,
        })
    return json.dumps({"speech_regions": entries}, indent=2)


def format_txt(annotation: Any) -> str:
    """Format VAD output as human-readable text."""
    lines = []
    total_speech = 0.0
    for segment, _, label in annotation.itertracks(yield_label=True):
        duration = segment.end - segment.start
        total_speech += duration
        start_m, start_s = divmod(segment.start, 60)
        end_m, end_s = divmod(segment.end, 60)
        lines.append(f"[{int(start_m):02d}:{start_s:05.2f} --> {int(end_m):02d}:{end_s:05.2f}] {label} ({duration:.2f}s)")
    lines.append(f"\nTotal speech: {total_speech:.2f}s")
    return "\n".join(lines)
