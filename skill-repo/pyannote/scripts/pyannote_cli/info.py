"""Info command — show audio file details and available models."""

from __future__ import annotations

from pathlib import Path

import typer

from pyannote_cli import app


@app.command()
def info(
    file: Path = typer.Argument(..., help="Audio file to inspect"),
) -> None:
    """Show audio file information (duration, sample rate, channels)."""
    from pyannote.audio import Audio

    if not file.exists():
        typer.echo(f"ERROR: File not found: {file}", err=True)
        raise typer.Exit(code=1)

    audio = Audio()
    waveform, sample_rate = audio(file)
    duration = waveform.shape[1] / sample_rate
    channels = waveform.shape[0]

    typer.echo(f"File:        {file}")
    typer.echo(f"Duration:    {duration:.2f}s")
    typer.echo(f"Sample rate: {sample_rate} Hz")
    typer.echo(f"Channels:    {channels}")
