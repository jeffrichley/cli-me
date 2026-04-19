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
# Source: `pandoc --pdf-engine=nonexistent in.md -o out.pdf` reports the
# authoritative list pandoc accepts. Keep in sync with that list.
PDF_ENGINES = (
    "pdflatex",
    "pdflatex-dev",
    "xelatex",
    "lualatex",
    "lualatex-dev",
    "tectonic",
    "latexmk",
    "context",
    "wkhtmltopdf",
    "weasyprint",
    "prince",
    "pagedjs-cli",
    "typst",
    "groff",
    "pdfroff",
)

# Subset of PDF_ENGINES that consume LaTeX source (vs HTML or other formats).
# Used by templates that are LaTeX-specific (e.g. Eisvogel) to validate
# `--pdf-engine` choices upfront.
LATEX_PDF_ENGINES = frozenset({
    "pdflatex",
    "pdflatex-dev",
    "xelatex",
    "lualatex",
    "lualatex-dev",
    "tectonic",
    "latexmk",
    "context",
})


@lru_cache(maxsize=1)
def find_pandoc() -> str:
    """Locate the pandoc binary or exit with install instructions."""
    path = shutil.which("pandoc")
    if path is not None:
        return path
    # Windows winget default install locations not always on PATH for fresh shells.
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            r"C:\Program Files\Pandoc\pandoc.exe",
            r"C:\Program Files (x86)\Pandoc\pandoc.exe",
        ]
        if local_appdata:
            # winget user-scope install location
            candidates.append(str(Path(local_appdata) / "Pandoc" / "pandoc.exe"))
        for candidate in candidates:
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

    Returns 'unknown' if pandoc fails to print a parseable version line.
    Forwards stderr to the user so a broken pandoc install is visible
    (rather than silently propagating "unknown" with exit 0).
    """
    exe = find_pandoc()
    result = subprocess.run(
        [exe, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and result.stderr:
        typer.echo(result.stderr, err=True, nl=False)
    first_line = result.stdout.split("\n", 1)[0]
    # "pandoc 3.9.0.2"
    parts = first_line.split()
    if len(parts) >= 2 and parts[0].lower() == "pandoc":
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
    forward_stderr_on_success: bool = True,
) -> subprocess.CompletedProcess:
    """Run a pandoc subprocess with sensible defaults.

    Behavior:
    - On success: returns the CompletedProcess. If ``capture`` is True and
      ``forward_stderr_on_success`` is True (default), pandoc's stderr is
      echoed to our stderr — so deprecation warnings (`--self-contained`),
      citeproc "citation not found" warnings, and similar non-fatal messages
      reach the user instead of being silently swallowed.
    - On non-zero exit (when ``check`` is True): forwards pandoc's stderr to
      our stderr verbatim, then raises ``typer.Exit(returncode)``. The user
      sees pandoc's actual error message, not a Python ``CalledProcessError``
      traceback.

    Pandoc has no interactive prompts. Pandoc DOES read from stdin if no
    input file is given, which would silently hang in agent contexts —
    callers are responsible for ensuring an input file is present in ``args``.
    """
    exe = find_pandoc()
    cmd = [exe] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=check,
        )
    except subprocess.CalledProcessError as e:
        # Forward pandoc's own stderr (which contains the real error message)
        # to the user instead of letting Typer/Rich render a Python traceback.
        if e.stderr:
            typer.echo(e.stderr, err=True, nl=False)
        raise typer.Exit(code=e.returncode)
    if capture and forward_stderr_on_success and result.stderr:
        typer.echo(result.stderr, err=True, nl=False)
    return result


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
