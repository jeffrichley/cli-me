"""Logic for `templates eisvogel` — convert to PDF using bundled Eisvogel.

Resolves the bundled `eisvogel.latex` template via
:func:`pandoc_cli.backend.bundled_template_path`, validates that a LaTeX
PDF engine is available, then forwards optional flags (`--toc`,
`--variable KEY=VALUE`, `--pdf-engine`) to pandoc.

Notes
-----
- Default engine: ``xelatex`` if available (Eisvogel recommends it), else
  ``pdflatex``. If neither is on PATH, exit 1 with an install hint.
- Explicit ``--pdf-engine`` is validated against ``backend.LATEX_PDF_ENGINES``
  upfront; non-LaTeX engines (weasyprint, wkhtmltopdf, prince, pagedjs-cli,
  typst, groff, pdfroff) are rejected before pandoc is ever invoked.
- OUTPUT extension non-`.pdf`: emit a stderr warning but proceed — pandoc
  honors the explicit ``-o`` regardless.
- OUTPUT == ``"-"`` (stdout): refused early — pandoc cannot stream a binary
  PDF to a terminal cleanly.
- Bundled template missing: exit 1 with a helpful message (someone may
  have deleted ``scripts/templates/eisvogel.latex`` after install).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli import backend
from pandoc_cli.backend import (
    LATEX_PDF_ENGINES,
    bundled_template_path,
    find_pdf_engines,
    report_success,
    run_pandoc,
)

# Engines we'll auto-pick from when the user doesn't pass --pdf-engine.
# Order matters: xelatex first because Eisvogel's README recommends it for
# the title-page font handling; pdflatex as a workable fallback.
_DEFAULT_ENGINE_PREFERENCE = ("xelatex", "pdflatex")


def _pick_default_engine(available: list[str]) -> Optional[str]:
    """Return the first engine in `_DEFAULT_ENGINE_PREFERENCE` that is available."""
    for engine in _DEFAULT_ENGINE_PREFERENCE:
        if engine in available:
            return engine
    return None


def build_args(
    input: str,
    output: str,
    template_path: str,
    *,
    pdf_engine: str,
    toc: bool = False,
    variable: Optional[list[str]] = None,
) -> list[str]:
    """Construct the pandoc argv list for a `templates eisvogel` invocation.

    Pure function: no filesystem checks, no subprocess calls.
    """
    args: list[str] = [
        str(input),
        "-o",
        str(output),
        "--template",
        str(template_path),
        f"--pdf-engine={pdf_engine}",
    ]

    if toc:
        args.append("--toc")

    for entry in variable or []:
        args.extend(["--variable", entry])

    return args


def run_eisvogel(
    input: str,
    output: str,
    *,
    toc: bool = False,
    variable: Optional[list[str]] = None,
    pdf_engine: Optional[str] = None,
) -> None:
    """Validate inputs, resolve the bundled template, run pandoc, report.

    Raises
    ------
    typer.Exit(1)
        If the input file is missing, the bundled Eisvogel template was
        deleted, or no LaTeX PDF engine is on PATH.
    """
    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"ERROR: Input file not found: {input}", err=True)
        raise typer.Exit(code=1)

    # Pandoc cannot stream a binary PDF to a terminal; refuse early so the
    # user gets a clear message rather than corrupted bytes or a pandoc-side
    # complaint about binary stdout.
    if output == "-":
        typer.echo(
            "ERROR: Eisvogel produces a binary PDF; OUTPUT '-' (stdout) is not supported.\n"
            "Pass an explicit output path (e.g. out.pdf).",
            err=True,
        )
        raise typer.Exit(code=1)

    eisvogel_path = bundled_template_path("eisvogel.latex")
    if not eisvogel_path.exists():
        typer.echo(
            f"ERROR: Bundled Eisvogel template not found at {eisvogel_path}.\n"
            "It ships with the skill at scripts/templates/eisvogel.latex.\n"
            "Re-install the pandoc skill to restore it.",
            err=True,
        )
        raise typer.Exit(code=1)

    # Resolve engine: explicit flag wins; otherwise pick from preferences.
    if pdf_engine is not None:
        # Eisvogel is a LaTeX template — reject HTML/Typst/groff engines
        # upfront with an actionable message instead of letting pandoc fail
        # mid-run with a less obvious error.
        if pdf_engine not in LATEX_PDF_ENGINES:
            allowed = sorted(LATEX_PDF_ENGINES)
            typer.echo(
                f"ERROR: Eisvogel is a LaTeX template; --pdf-engine must be one of "
                f"{allowed}. You passed {pdf_engine!r}.",
                err=True,
            )
            raise typer.Exit(code=1)
    else:
        available = find_pdf_engines()
        chosen = _pick_default_engine(available)
        if chosen is None:
            typer.echo(
                "ERROR: Eisvogel needs a LaTeX PDF engine but none were found on PATH.\n"
                "Install one of:\n"
                "  Windows: install MiKTeX (https://miktex.org/) — provides pdflatex/xelatex\n"
                "  macOS:   brew install --cask mactex\n"
                "  Linux:   apt install texlive-xetex\n"
                "Re-run with --pdf-engine=ENGINE once installed.",
                err=True,
            )
            raise typer.Exit(code=1)
        pdf_engine = chosen

    if Path(output).suffix.lower() != ".pdf":
        typer.echo(
            f"WARNING: Eisvogel produces PDF, but OUTPUT is {output!r} "
            "(no .pdf extension). Pandoc honors -o verbatim, so the output "
            "file may not be a usable PDF.",
            err=True,
        )

    args = build_args(
        input,
        output,
        str(eisvogel_path),
        pdf_engine=pdf_engine,
        toc=toc,
        variable=variable,
    )

    run_pandoc(args, check=True, capture=True)

    # ``output == "-"`` is rejected upfront; safe to report unconditionally.
    report_success(output)
