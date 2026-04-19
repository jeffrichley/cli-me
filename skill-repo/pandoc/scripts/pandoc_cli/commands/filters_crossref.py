"""Logic for ``filters crossref-check`` — verify pandoc-crossref availability.

Delegates the missing-binary path to ``backend.check_pandoc_crossref`` (which
exits 1 with install instructions). When present, additionally probes the
binary's ``--version`` output so the wiki and agents can spot version skew
against the installed pandoc release.
"""

from __future__ import annotations

import subprocess

import typer

from pandoc_cli.backend import check_pandoc_crossref


def run_crossref_check() -> dict[str, str]:
    """Return ``{"path": <abs path>, "version": <version string>}``.

    Raises ``typer.Exit(code=1)`` (via ``check_pandoc_crossref``) when the
    binary is not on PATH; the helper has already printed install instructions
    by then.

    Also raises ``typer.Exit(code=1)`` when the binary IS on PATH but
    ``--version`` returns an empty string (e.g. a corrupt binary or an
    incompatible release that prints nothing). Without this guard, callers
    would see ``version: `` printed with no value and no error — a confusing
    silent failure.

    The version string is whatever ``pandoc-crossref --version`` prints on
    stdout, stripped of trailing whitespace. Pandoc-crossref's CLI prints a
    one-line banner like ``pandoc-crossref v0.3.17.0`` followed by build
    metadata; we keep the whole thing rather than try to parse a single
    semver, since the matrix in references/gotchas.md uses the full string.
    """
    path = check_pandoc_crossref()
    result = subprocess.run(
        [path, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    version = (result.stdout or result.stderr).strip()
    if not version:
        typer.echo(
            f"ERROR: pandoc-crossref present but '--version' returned no output. "
            f"The binary may be corrupt or incompatible. Path: {path}",
            err=True,
        )
        raise typer.Exit(code=1)
    return {"path": path, "version": version}
