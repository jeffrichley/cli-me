"""Info command group — inspect speakers, languages, and device info."""

from typing import Annotated, Optional

import typer

from . import app
from .backend import load_model
from .commands import info_device, info_speakers, info_languages

info_app = typer.Typer(help="Inspect speakers, languages, and device info.", no_args_is_help=True)
app.add_typer(info_app, name="info")


@info_app.command()
def device() -> None:
    """Show GPU/CPU status and available hardware."""
    info = info_device.get_device_info()
    typer.echo(info_device.format_device_info(info, pretty=True))


@info_app.command()
def speakers(
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    pretty: Annotated[bool, typer.Option("--pretty", help="Human-readable output")] = False,
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """List available built-in speakers."""
    model = load_model(model_size, device)
    speaker_list = info_speakers.get_speakers(model)
    typer.echo(info_speakers.format_speakers(speaker_list, pretty=pretty))


@info_app.command()
def languages(
    model_size: Annotated[str, typer.Option("--model", help="Model size (1.7b or 0.6b)")] = "1.7b",
    pretty: Annotated[bool, typer.Option("--pretty", help="Human-readable output")] = False,
    device: Annotated[Optional[str], typer.Option(help="Force device (cuda, cpu, mps)")] = None,
) -> None:
    """List supported languages."""
    model = load_model(model_size, device)
    lang_list = info_languages.get_languages(model)
    typer.echo(info_languages.format_languages(lang_list, pretty=pretty))
