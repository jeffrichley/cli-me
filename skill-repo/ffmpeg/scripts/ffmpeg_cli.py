"""ffmpeg_cli: Agent-native CLI for ffmpeg.

Calls the real ffmpeg/ffprobe binary — does not process media in Python.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="ffmpeg-cli",
    help="Agent-native CLI for ffmpeg.",
    no_args_is_help=True,
)

# Command group sub-apps
convert_app = typer.Typer(help="Format conversion, compression, platform encoding")
extract_app = typer.Typer(help="Trim clips, extract audio, frames, sprites")
transform_app = typer.Typer(help="Resize, crop, speed, watermark, subtitles, rotate, fade")
audio_app = typer.Typer(help="Normalize loudness, denoise, remove silence, music ducking")
combine_app = typer.Typer(help="Concatenate, mux, image sequences, compositing")
stream_app = typer.Typer(help="HLS, DASH, multi-bitrate, RTMP, fake live")
util_app = typer.Typer(help="Batch transcode, probe, screen capture, surveillance")

app.add_typer(convert_app, name="convert")
app.add_typer(extract_app, name="extract")
app.add_typer(transform_app, name="transform")
app.add_typer(audio_app, name="audio")
app.add_typer(combine_app, name="combine")
app.add_typer(stream_app, name="stream")
app.add_typer(util_app, name="util")


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

def find_executable(name: str) -> str:
    """Locate ffmpeg or ffprobe, or exit with install instructions."""
    path = shutil.which(name)
    if path is None:
        typer.echo(
            f"ERROR: {name} not found in PATH.\n"
            "Install from: https://ffmpeg.org/download.html\n"
            "  Windows: winget install ffmpeg\n"
            "  macOS:   brew install ffmpeg\n"
            "  Linux:   apt install ffmpeg",
            err=True,
        )
        raise typer.Exit(code=1)
    return path


def detect_version() -> str:
    """Return the ffmpeg version string."""
    exe = find_executable("ffmpeg")
    result = subprocess.run([exe, "-version"], capture_output=True, text=True)
    first_line = result.stdout.split("\n")[0]
    # "ffmpeg version N.N.N ..." or "ffmpeg version N.N.N-ubuntu..."
    parts = first_line.split()
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


def run_ffmpeg(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run an ffmpeg command. Returns CompletedProcess."""
    exe = find_executable("ffmpeg")
    cmd = [exe] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def run_ffprobe(args: list[str]) -> subprocess.CompletedProcess:
    """Run an ffprobe command. Returns CompletedProcess."""
    exe = find_executable("ffprobe")
    cmd = [exe] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_json(input_path: str) -> dict:
    """Run ffprobe and return parsed JSON."""
    result = run_ffprobe([
        "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        input_path,
    ])
    return json.loads(result.stdout)


def get_duration(input_path: str) -> float:
    """Get duration in seconds from ffprobe."""
    data = probe_json(input_path)
    return float(data.get("format", {}).get("duration", 0))


def report_success(output_path: str) -> None:
    """Report successful output with file size."""
    path = Path(output_path)
    if path.exists():
        size = path.stat().st_size
        if size > 1_000_000:
            size_str = f"{size / 1_000_000:.1f} MB"
        elif size > 1_000:
            size_str = f"{size / 1_000:.1f} KB"
        else:
            size_str = f"{size} bytes"
        typer.echo(f"Output: {output_path} ({size_str})")
    else:
        typer.echo(f"Output: {output_path}")


# ---------------------------------------------------------------------------
# Placeholder: command implementations will be added in Tasks 10-16
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    app()
