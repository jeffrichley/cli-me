"""Logic for `templates print` — emit pandoc's default template for a format.

Mirrors `pandoc --print-default-template=FORMAT` and returns the captured
stdout to the caller. Exits via the underlying `subprocess.CalledProcessError`
when pandoc rejects the format (unknown writer); the typer dispatch surfaces
that exit code.
"""

from __future__ import annotations

import re

import typer

from pandoc_cli.backend import run_pandoc


# Matches the first pandoc extension marker (`+ext` or `-ext`) in a format
# spec like `markdown+smart-implicit_figures`.
_EXT_SUFFIX_RE = re.compile(r"[+-].*$")


def _strip_extensions(format: str) -> str:
    """Strip pandoc extension suffixes from a format spec.

    ``markdown+yaml_metadata_block-implicit_figures`` -> ``markdown``.
    Bare format names pass through unchanged.
    """
    return _EXT_SUFFIX_RE.sub("", format)


def run_print(format: str) -> str:
    """Return pandoc's default template for `format` as a string.

    Pandoc's ``--print-default-template=FORMAT`` accepts only bare format
    names (e.g. ``markdown``, ``latex``, ``html5``); it does NOT accept
    extension-suffixed specs like ``markdown+smart``. This wrapper handles
    that by **stripping** any ``+ext`` / ``-ext`` suffix before forwarding,
    so callers can pass the same format spec they'd use with ``-t`` /
    ``--to`` and get the template for the underlying writer. A stripped
    suffix is reported on stderr so the user knows it happened.

    Parameters
    ----------
    format
        A pandoc writer name (e.g. ``latex``, ``html5``, ``revealjs``,
        ``markdown+smart``). Extensions are stripped before forwarding.

    Returns
    -------
    str
        The template text exactly as pandoc emitted it on stdout.

    Raises
    ------
    subprocess.CalledProcessError
        If pandoc exits non-zero (unknown format, missing writer, etc.).
        Re-raised by ``run_pandoc(check=True)`` so the typer layer can convert
        it into the appropriate exit code.
    """
    bare = _strip_extensions(format)
    if bare != format:
        typer.echo(
            f"NOTE: --print-default-template requires a bare format name; "
            f"using {bare!r} (stripped {format!r}).",
            err=True,
        )
    args = [f"--print-default-template={bare}"]
    result = run_pandoc(args, check=True, capture=True)
    return result.stdout
