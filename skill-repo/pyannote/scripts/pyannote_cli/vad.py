"""VAD command — thin CLI wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pyannote_cli import app
from pyannote_cli.backend import load_pipeline
from pyannote_cli.commands.vad import run_vad, format_rttm, format_json, format_txt


@app.command()
def vad(
    file: Path = typer.Argument(..., help="Audio file to analyze"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file (default: stdout)"),
    format: str = typer.Option("rttm", "--format", "-f", help="Output format: rttm, json, txt"),
    device: str = typer.Option("auto", help="Device: cpu, cuda, mps, auto"),
    token: Optional[str] = typer.Option(None, help="HuggingFace token (default: HF_TOKEN env)"),
) -> None:
    """Detect speech regions in an audio file (voice activity detection)."""
    if not file.exists():
        typer.echo(f"ERROR: File not found: {file}", err=True)
        raise typer.Exit(code=1)

    pipeline = load_pipeline(
        "pyannote/speaker-diarization-community-1",
        token=token,
        device=device,
    )

    result = run_vad(pipeline, file)

    formatters = {"rttm": format_rttm, "json": format_json, "txt": format_txt}
    formatter = formatters.get(format)
    if formatter is None:
        typer.echo(f"ERROR: Unknown format '{format}'. Use: rttm, json, txt", err=True)
        raise typer.Exit(code=1)

    text = formatter(result, filename=file.stem) if format == "rttm" else formatter(result)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n")
        typer.echo(f"Saved to {output}")
    else:
        typer.echo(text)
