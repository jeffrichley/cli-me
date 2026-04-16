"""pyannote.audio CLI — speaker diarization and audio analysis."""

import typer

app = typer.Typer(
    name="pyannote-cli",
    help="Agent-native CLI for pyannote.audio — diarize, detect speech, verify speakers, extract embeddings.",
    no_args_is_help=True,
)

# Register command modules — import triggers @app.command() decoration
import pyannote_cli.info  # noqa: E402, F401
