"""Verify command — thin CLI wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pyannote_cli import app
from pyannote_cli.backend import load_inference
from pyannote_cli.commands.verify import verify_speakers


@app.command()
def verify(
    file_a: Path = typer.Argument(..., help="First audio file"),
    file_b: Path = typer.Argument(..., help="Second audio file"),
    threshold: float = typer.Option(0.7, help="Similarity threshold for same speaker"),
    model: str = typer.Option("resnet34", help="Embedding model: resnet34, resnet152"),
    device: str = typer.Option("auto", help="Device: cpu, cuda, mps, auto"),
    token: Optional[str] = typer.Option(None, help="HuggingFace token (default: HF_TOKEN env)"),
) -> None:
    """Compare two audio files to determine if same speaker."""
    for f in (file_a, file_b):
        if not f.exists():
            typer.echo(f"ERROR: File not found: {f}", err=True)
            raise typer.Exit(code=1)

    model_map = {
        "resnet34": "pyannote/wespeaker-resnet34-voxceleb",
        "resnet152": "pyannote/wespeaker-resnet152-voxceleb",
    }
    model_name = model_map.get(model)
    if model_name is None:
        typer.echo(f"ERROR: Unknown model '{model}'. Use: resnet34, resnet152", err=True)
        raise typer.Exit(code=1)

    inference = load_inference(model_name, token=token, device=device, window="whole")

    result = verify_speakers(inference, file_a, file_b, threshold=threshold)

    verdict = "SAME speaker" if result["same_speaker"] else "DIFFERENT speakers"
    typer.echo(f"Score:     {result['score']:.4f}")
    typer.echo(f"Threshold: {result['threshold']:.4f}")
    typer.echo(f"Result:    {verdict}")
