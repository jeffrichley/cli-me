"""Embed command — thin CLI wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pyannote_cli import app
from pyannote_cli.backend import load_inference
from pyannote_cli.commands.embed import run_embed, format_json, format_numpy


@app.command()
def embed(
    file: Path = typer.Argument(..., help="Audio file to extract embedding from"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file (default: stdout as JSON)"),
    model: str = typer.Option("resnet34", help="Embedding model: resnet34, embedding"),
    device: str = typer.Option("auto", help="Device: cpu, cuda, mps, auto"),
    token: Optional[str] = typer.Option(None, help="HuggingFace token (default: HF_TOKEN env)"),
) -> None:
    """Extract speaker embedding vector from an audio file."""
    if not file.exists():
        typer.echo(f"ERROR: File not found: {file}", err=True)
        raise typer.Exit(code=1)

    model_map = {
        "resnet34": "pyannote/wespeaker-voxceleb-resnet34-LM",
        "embedding": "pyannote/embedding",
    }
    model_name = model_map.get(model)
    if model_name is None:
        typer.echo(f"ERROR: Unknown model '{model}'. Use: resnet34, embedding", err=True)
        raise typer.Exit(code=1)

    inference = load_inference(model_name, token=token, device=device, window="whole")
    embedding = run_embed(inference, file)

    if output and output.suffix == ".npy":
        output.parent.mkdir(parents=True, exist_ok=True)
        format_numpy(embedding, output)
        typer.echo(f"Saved {len(embedding)}-dim embedding to {output}")
    elif output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(format_json(embedding, file) + "\n")
        typer.echo(f"Saved {len(embedding)}-dim embedding to {output}")
    else:
        typer.echo(format_json(embedding, file))
