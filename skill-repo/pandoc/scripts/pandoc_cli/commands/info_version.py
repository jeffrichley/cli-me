"""Logic for `info version` — return the installed pandoc version string."""

from __future__ import annotations

from pandoc_cli.backend import detect_version


def run_version() -> str:
    """Return the installed pandoc version (e.g. '3.9.0.2').

    Returns 'unknown' if pandoc's `--version` output cannot be parsed.
    Raises typer.Exit via `find_pandoc()` if pandoc itself is not installed.
    """
    return detect_version()
