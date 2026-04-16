"""Clone command group — voice cloning from reference audio."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import load_model, save_audio
from .commands import clone_text

clone_app = typer.Typer(help="Voice cloning from reference audio.", no_args_is_help=True)
app.add_typer(clone_app, name="clone")


@clone_app.command()
def text(
    content: Annotated[str, typer.Argument(help="Text to synthesize")],
    reference: Annotated[str, typer.Option("--reference", help="Path to reference audio file (3+ seconds)")],
    ref_text: Annotated[str, typer.Option("--ref-text", help="Transcript of the reference audio")],
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")],
    lang: Annotated[str, typer.Option(help="Language (English, Chinese, Auto, etc.)")] = "Auto",
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (wav, mp3, flac, ogg)")] = "wav",
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """Clone a voice from reference audio and generate speech."""
    model = load_model(model_size, device)
    try:
        audio, sr = clone_text.clone_speech(
            model,
            text=content,
            reference=reference,
            ref_text=ref_text,
            language=lang,
        )
    except (FileNotFoundError, ValueError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)
    path = save_audio(audio, sr, output, format=format)
    typer.echo(f"Saved to {path}")
