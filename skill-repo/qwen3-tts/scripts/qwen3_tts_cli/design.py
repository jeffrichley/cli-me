"""Design command group — voice design from natural language descriptions."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import load_design_model, save_audio
from .commands import design_text

design_app = typer.Typer(help="Voice design from natural language descriptions.", no_args_is_help=True)
app.add_typer(design_app, name="design")


@design_app.command()
def text(
    content: Annotated[str, typer.Argument(help="Text to synthesize")],
    description: Annotated[str, typer.Option("--description", help="Natural language voice description")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")],
    lang: Annotated[str, typer.Option(help="Language (English, Chinese, Auto, etc.)")] = "Auto",
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (wav, mp3, flac, ogg)")] = "wav",
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """Design a voice from a natural language description and generate speech."""
    try:
        model = load_design_model(model_size, device)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    try:
        audio, sr = design_text.design_speech(
            model,
            text=content,
            description=description,
            language=lang,
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    path = save_audio(audio, sr, output, format=format)
    typer.echo(f"Saved to {path}")
