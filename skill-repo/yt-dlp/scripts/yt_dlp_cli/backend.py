"""Backend utilities for yt-dlp CLI — find executable, detect version, run commands."""

import shutil
import subprocess
import sys

import typer


def find_executable(name: str = "yt-dlp") -> str:
    """Find the yt-dlp executable or exit with install instructions."""
    path = shutil.which(name)
    if path is not None:
        return path

    # Windows: check common pip install locations not on PATH
    if sys.platform == "win32":
        import pathlib

        for scripts_dir in pathlib.Path.home().glob(
            "AppData/Roaming/Python/Python3*/Scripts"
        ):
            candidate = scripts_dir / f"{name}.exe"
            if candidate.exists():
                return str(candidate)
        for scripts_dir in pathlib.Path.home().glob(
            "AppData/Local/Programs/Python/Python3*/Scripts"
        ):
            candidate = scripts_dir / f"{name}.exe"
            if candidate.exists():
                return str(candidate)

    typer.echo(
        f"ERROR: {name} not found. Install with: pip install yt-dlp\n"
        f"Or see: https://github.com/yt-dlp/yt-dlp#installation",
        err=True,
    )
    raise typer.Exit(code=1)


def detect_version() -> str:
    """Detect installed yt-dlp version string (e.g., '2026.03.17')."""
    exe = find_executable()
    result = subprocess.run(
        [exe, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def run_command(
    args: list[str],
    check: bool = True,
    capture: bool = False,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    """Run a yt-dlp command and return the result.

    Args:
        args: Arguments to pass to yt-dlp (without the executable name).
        check: Raise on non-zero exit code.
        capture: Capture stdout/stderr instead of streaming.
        timeout: Timeout in seconds (None = no timeout).
    """
    exe = find_executable()
    cmd = [exe] + args
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
        timeout=timeout,
    )
