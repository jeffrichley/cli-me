"""Models command — list available pretrained models."""

import typer

from . import app
from .commands import list_models


@app.command("list-models")
def list_models_cmd() -> None:
    """List available pretrained Demucs models."""
    output = list_models.build_output()
    typer.echo(output)
