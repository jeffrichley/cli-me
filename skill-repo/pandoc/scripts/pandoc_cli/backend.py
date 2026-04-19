"""Backend helpers: pandoc binary discovery, version detection, subprocess invocation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import typer

# Engines pandoc supports for `-t pdf` (or via `--pdf-engine`). Each must be
# installed separately on PATH; pandoc errors if the chosen engine is missing.
PDF_ENGINES = (
    "pdflatex",
    "xelatex",
    "lualatex",
    "tectonic",
    "latexmk",
    "context",
    "wkhtmltopdf",
    "weasyprint",
    "prince",
    "pagedjs-cli",
    "typst",
)


@lru_cache(maxsize=1)
def find_pandoc() -> str:
    """Locate the pandoc binary or exit with install instructions."""
    path = shutil.which("pandoc")
    if path is not None:
        return path
    # Windows winget default install location not always on PATH for fresh shells.
    if sys.platform == "win32":
        for candidate in (
            r"C:\Program Files\Pandoc\pandoc.exe",
            r"C:\Program Files (x86)\Pandoc\pandoc.exe",
        ):
            if Path(candidate).exists():
                return candidate
    typer.echo(
        "ERROR: pandoc not found in PATH.\n"
        "Install:\n"
        "  Windows: winget install JohnMacFarlane.Pandoc\n"
        "  macOS:   brew install pandoc\n"
        "  Linux:   apt install pandoc  (or: dnf, pacman, etc.)\n"
        "Verify:    pandoc --version",
        err=True,
    )
    raise typer.Exit(code=1)


@lru_cache(maxsize=1)
def detect_version() -> str:
    """Return the installed pandoc version string (e.g. '3.9.0.2').

    Returns 'unknown' if pandoc fails to print a parseable version line —
    `check=False` so a broken pandoc install doesn't crash unrelated commands.
    """
    exe = find_pandoc()
    result = subprocess.run(
        [exe, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    first_line = result.stdout.split("\n", 1)[0]
    # "pandoc 3.9.0.2"
    parts = first_line.split()
    if len(parts) >= 2:
        return parts[1]
    return "unknown"


def check_pandoc_crossref() -> str:
    """Locate pandoc-crossref binary or exit with install instructions.

    Used by filter commands that require pandoc-crossref. The binary's version
    must match the installed pandoc version; the wrapper does NOT auto-install.
    """
    path = shutil.which("pandoc-crossref")
    if path is not None:
        return path
    pandoc_ver = detect_version()
    typer.echo(
        "ERROR: pandoc-crossref not found in PATH.\n"
        f"Your pandoc version is {pandoc_ver}; install a matching crossref release:\n"
        "  Binary:  https://github.com/lierdakil/pandoc-crossref/releases\n"
        "           (must match your pandoc version)\n"
        "  Cabal:   cabal install pandoc-crossref\n"
        "  Choco:   choco install pandoc-crossref  (Windows)\n"
        "  Brew:    brew install pandoc-crossref   (macOS)",
        err=True,
    )
    raise typer.Exit(code=1)


def find_pdf_engines() -> list[str]:
    """Return the list of PDF engines actually available on PATH."""
    return [eng for eng in PDF_ENGINES if shutil.which(eng) is not None]


def run_pandoc(
    args: list[str],
    *,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """Run a pandoc subprocess with sensible defaults.

    `check=True` raises on non-zero exit. `capture=True` returns stdout/stderr
    as strings on the result. Pandoc has no interactive prompts to suppress —
    no `-y` equivalent needed — but if no input file is provided, pandoc reads
    from stdin, which would silently hang in agent contexts. Callers are
    responsible for ensuring an input file is present in `args`.
    """
    exe = find_pandoc()
    cmd = [exe] + args
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )


def report_success(output_path: str) -> None:
    """Echo a success line with file size for the produced output."""
    p = Path(output_path)
    if p.exists():
        size = p.stat().st_size
        if size > 1_000_000:
            size_str = f"{size / 1_000_000:.1f} MB"
        elif size > 1_000:
            size_str = f"{size / 1_000:.1f} KB"
        else:
            size_str = f"{size} bytes"
        typer.echo(f"Wrote: {output_path} ({size_str})")
    else:
        typer.echo(f"Wrote: {output_path}")


def bundled_template_path(name: str) -> Path:
    """Return the path to a bundled template (e.g. 'eisvogel.latex')."""
    here = Path(__file__).resolve().parent.parent
    return here / "templates" / name
