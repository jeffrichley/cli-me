"""Separate command — split audio into stems."""

import subprocess
from typing import Annotated, Optional
from pathlib import Path

import typer

from . import app
from .backend import detect_device, run_command
from .commands import separate_audio


@app.command()
def separate(
    files: Annotated[
        list[Path],
        typer.Argument(help="Audio files to separate."),
    ],
    model: Annotated[
        str,
        typer.Option("--model", "-n", help="Pretrained model name."),
    ] = "htdemucs",
    repo: Annotated[
        Optional[str],
        typer.Option(help="Path to folder with custom models."),
    ] = None,
    device: Annotated[
        Optional[str],
        typer.Option(
            help="Compute device: auto (default), cuda, cuda:N, cpu.",
        ),
    ] = None,
    shifts: Annotated[
        int,
        typer.Option(help="Random shift augmentations (higher = better quality, slower)."),
    ] = 1,
    overlap: Annotated[
        Optional[float],
        typer.Option(help="Overlap between chunks (0.0-1.0)."),
    ] = None,
    segment: Annotated[
        Optional[int],
        typer.Option(help="Chunk length in seconds (lower = less VRAM)."),
    ] = None,
    no_split: Annotated[
        bool,
        typer.Option("--no-split", help="Disable chunking (uses more memory)."),
    ] = False,
    two_stems: Annotated[
        Optional[str],
        typer.Option(help="Extract one stem + complement (e.g., vocals, drums, bass)."),
    ] = None,
    format: Annotated[
        Optional[str],
        typer.Option(help="Output format: wav (default), mp3, flac."),
    ] = None,
    mp3_bitrate: Annotated[
        Optional[int],
        typer.Option(help="MP3 bitrate in kbps (default 320)."),
    ] = None,
    mp3_preset: Annotated[
        Optional[int],
        typer.Option(help="MP3 encoder quality (2=best, 7=fastest)."),
    ] = None,
    int24: Annotated[
        bool,
        typer.Option("--int24", help="Save as 24-bit WAV."),
    ] = False,
    float32: Annotated[
        bool,
        typer.Option("--float32", help="Save as 32-bit float WAV."),
    ] = False,
    clip_mode: Annotated[
        Optional[str],
        typer.Option(help="Clipping strategy: rescale (default), clamp."),
    ] = None,
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output directory."),
    ] = None,
    jobs: Annotated[
        Optional[int],
        typer.Option("--jobs", "-j", help="Parallel workers (CPU only)."),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Verbose output."),
    ] = False,
) -> None:
    """Separate audio files into stems (vocals, drums, bass, other)."""
    # Validate input files exist
    for f in files:
        if not f.exists():
            typer.echo(f"ERROR: File not found: {f}", err=True)
            raise typer.Exit(code=1)

    # Report detected device
    if device is None:
        detected = detect_device()
        typer.echo(f"Device: {detected} (auto-detected)")
    else:
        typer.echo(f"Device: {device}")

    try:
        args = separate_audio.build_args(
            [str(f) for f in files],
            model=model,
            repo=repo,
            device=device,
            shifts=shifts,
            overlap=overlap,
            segment=segment,
            no_split=no_split,
            two_stems=two_stems,
            format=format,
            mp3_bitrate=mp3_bitrate,
            mp3_preset=mp3_preset,
            int24=int24,
            float32=float32,
            clip_mode=clip_mode,
            output=output,
            jobs=jobs,
            verbose=verbose,
        )
    except ValueError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Separating {len(files)} file(s) with model '{model}'...")
    try:
        result = run_command(args, timeout=3600, check=False, capture=True)
    except subprocess.TimeoutExpired:
        typer.echo(
            "ERROR: Separation timed out after 1 hour. "
            "Try fewer files, a faster model, or fewer shifts.",
            err=True,
        )
        raise typer.Exit(code=1)
    if result.stdout:
        typer.echo(result.stdout.rstrip())
    if result.stderr and result.returncode == 0:
        typer.echo(result.stderr.rstrip(), err=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        fatal_lines = [l for l in stderr.splitlines() if "FATAL" in l]
        msg = fatal_lines[0] if fatal_lines else stderr[-500:] if stderr else "unknown error"
        typer.echo(f"ERROR: Demucs failed (exit code {result.returncode}): {msg}", err=True)
        raise typer.Exit(code=result.returncode)
    typer.echo("Done.")
