"""Logic for info speakers command."""

import json


def get_speakers(model) -> list[str]:
    """Get supported speakers from a loaded model."""
    return model.get_supported_speakers()


def format_speakers(speakers: list[str], pretty: bool = False) -> str:
    """Format speaker list as JSON or human-readable."""
    if pretty:
        lines = [f"Available speakers ({len(speakers)}):"]
        for i, s in enumerate(speakers, 1):
            lines.append(f"  {i}. {s}")
        return "\n".join(lines)
    return json.dumps(speakers, indent=2)
