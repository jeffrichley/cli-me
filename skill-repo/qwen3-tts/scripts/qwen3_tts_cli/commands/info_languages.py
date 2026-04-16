"""Logic for info languages command."""

import json


def get_languages(model) -> list[str]:
    """Get supported languages from a loaded model."""
    return model.get_supported_languages()


def format_languages(languages: list[str], pretty: bool = False) -> str:
    """Format language list as JSON or human-readable."""
    if pretty:
        lines = [f"Supported languages ({len(languages)}):"]
        for i, lang in enumerate(languages, 1):
            lines.append(f"  {i}. {lang}")
        return "\n".join(lines)
    return json.dumps(languages, indent=2)
