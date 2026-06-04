"""Backend helpers for GIMP binary discovery and execution."""

from __future__ import annotations

import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import typer


@lru_cache(maxsize=1)
def find_executable() -> str:
    """Find GIMP executable path or exit with install instructions."""
    candidates = [
        "gimp-console-3.0",
        "gimp-console-2.10",
        "gimp-console",
        "gimp-3.0",
        "gimp-2.10",
        "gimp",
    ]
    for name in candidates:
        resolved = shutil.which(name)
        if resolved:
            return resolved

    if sys.platform == "win32":
        windows_paths = [
            Path("C:/Program Files/GIMP 3/bin/gimp-console-3.0.exe"),
            Path("C:/Program Files/GIMP 3/bin/gimp-3.0.exe"),
            Path("C:/Program Files/GIMP 2/bin/gimp-console-2.10.exe"),
            Path("C:/Program Files/GIMP 2/bin/gimp-2.10.exe"),
        ]
        for path in windows_paths:
            if path.exists():
                return str(path)

    typer.echo(
        "ERROR: GIMP executable not found.\n"
        "Install GIMP and ensure gimp/gimp-console is on PATH.\n"
        "Windows: winget install GIMP.GIMP\n"
        "macOS:   brew install --cask gimp\n"
        "Linux:   apt install gimp",
        err=True,
    )
    raise typer.Exit(code=1)


def run_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run GIMP command and forward stderr on failure."""
    exe = find_executable()
    cmd = [exe] + args
    try:
        return subprocess.run(cmd, text=True, capture_output=True, check=check)
    except subprocess.CalledProcessError as exc:
        if exc.stderr:
            typer.echo(exc.stderr, err=True, nl=False)
        raise typer.Exit(code=exc.returncode)


def detect_version() -> str:
    """Return installed GIMP version string."""
    result = run_command(["--version"], check=False)
    if result.returncode != 0:
        if result.stderr:
            typer.echo(result.stderr, err=True, nl=False)
        raise typer.Exit(code=result.returncode)
    return result.stdout.strip()
