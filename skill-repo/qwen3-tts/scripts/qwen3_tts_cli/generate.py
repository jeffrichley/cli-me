"""Generate command group — text-to-speech with built-in speakers."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import load_model, save_audio
from .commands import generate_text

generate_app = typer.Typer(help="Text-to-speech generation with built-in speakers.", no_args_is_help=True)
app.add_typer(generate_app, name="generate")


@generate_app.command()
def text(
    content: Annotated[str, typer.Argument(help="Text to synthesize")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")],
    speaker: Annotated[str, typer.Option(help="Built-in speaker name")] = "Aiden",
    instruct: Annotated[Optional[str], typer.Option(help="Style/emotion instruction")] = None,
    lang: Annotated[str, typer.Option(help="Language (English, Chinese, Auto, etc.)")] = "Auto",
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (wav, mp3, flac, ogg)")] = "wav",
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """Generate speech from text using a built-in speaker."""
    model = load_model(model_size, device)
    try:
        audio, sr = generate_text.generate_speech(
            model,
            text=content,
            speaker=speaker,
            language=lang,
            instruct=instruct,
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    path = save_audio(audio, sr, output, format=format)
    typer.echo(f"Saved to {path}")
