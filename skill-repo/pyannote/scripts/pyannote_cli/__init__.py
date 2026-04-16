"""pyannote.audio CLI — speaker diarization and audio analysis."""

import typer

app = typer.Typer(
    name="pyannote-cli",
    help="Agent-native CLI for pyannote.audio — diarize, detect speech, verify speakers, extract embeddings.",
    no_args_is_help=True,
)

# Register command modules — import triggers @app.command() decoration
import pyannote_cli.info  # noqa: E402, F401
import pyannote_cli.diarize  # noqa: E402, F401
import pyannote_cli.vad  # noqa: E402, F401
import pyannote_cli.verify  # noqa: E402, F401
import pyannote_cli.embed  # noqa: E402, F401
