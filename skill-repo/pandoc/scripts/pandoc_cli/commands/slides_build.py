"""Logic for `slides build` — build a pandoc invocation and run it."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli.backend import find_pdf_engines, report_success, run_pandoc

_SLIDE_WRITERS = frozenset({"beamer", "revealjs"})


def build_args(
    input: str,
    output: str,
    *,
    to: str,
    from_: Optional[str] = None,
    slide_level: Optional[int] = None,
    incremental: bool = False,
    standalone: Optional[bool] = None,
    toc: bool = False,
    metadata: Optional[list[str]] = None,
    variable: Optional[list[str]] = None,
    pdf_engine: Optional[str] = None,
    embed_resources: bool = False,
) -> list[str]:
    """Construct the pandoc argv list for a `slides build` invocation."""
    args: list[str] = [str(input), "-o", str(output), "--to", to]

    if from_ is not None:
        args.extend(["--from", from_])
    if slide_level is not None:
        args.extend(["--slide-level", str(slide_level)])
    if incremental:
        args.append("--incremental")
    if standalone is True:
        args.append("--standalone")
    elif standalone is False:
        args.append("--standalone=false")
    if toc:
        args.append("--toc")

    for entry in metadata or []:
        args.extend(["--metadata", entry])

    if pdf_engine is not None:
        args.extend(["--pdf-engine", pdf_engine])
    for entry in variable or []:
        args.extend(["--variable", entry])
    if embed_resources:
        args.append("--embed-resources")

    return args


def _is_pdf_path(output: str) -> bool:
    """True when the destination is a PDF file (by extension)."""
    if output == "-":
        return False
    return Path(output).suffix.lower() == ".pdf"


def run_build(
    input: str,
    output: str,
    *,
    to: str,
    from_: Optional[str] = None,
    slide_level: Optional[int] = None,
    incremental: bool = False,
    standalone: Optional[bool] = None,
    toc: bool = False,
    metadata: Optional[list[str]] = None,
    variable: Optional[list[str]] = None,
    pdf_engine: Optional[str] = None,
    embed_resources: bool = False,
) -> None:
    """Validate slide-specific preconditions, then run pandoc."""
    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"ERROR: Input file not found: {input}", err=True)
        raise typer.Exit(code=1)

    if to not in _SLIDE_WRITERS:
        typer.echo("ERROR: --to must be one of: beamer, revealjs", err=True)
        raise typer.Exit(code=1)

    if to == "beamer" and embed_resources:
        typer.echo(
            "ERROR: --embed-resources is only supported for revealjs slide output.",
            err=True,
        )
        raise typer.Exit(code=1)

    if to == "revealjs" and pdf_engine is not None:
        typer.echo(
            "ERROR: --pdf-engine is only supported for beamer slide output.",
            err=True,
        )
        raise typer.Exit(code=1)

    if output == "-" and to == "beamer":
        typer.echo(
            "ERROR: Cannot write beamer slide output to stdout. Use a file path.",
            err=True,
        )
        raise typer.Exit(code=1)

    if pdf_engine is not None:
        available = find_pdf_engines()
        if pdf_engine not in available:
            available_str = ", ".join(available) if available else "(none found)"
            typer.echo(
                f"ERROR: PDF engine '{pdf_engine}' not found on PATH. "
                f"Available: {available_str}",
                err=True,
            )
            raise typer.Exit(code=1)

    if to == "beamer" and _is_pdf_path(output):
        engines = find_pdf_engines()
        if not engines:
            typer.echo(
                "ERROR: PDF output requested but no PDF engine found on PATH.",
                err=True,
            )
            raise typer.Exit(code=1)

    args = build_args(
        input,
        output,
        to=to,
        from_=from_,
        slide_level=slide_level,
        incremental=incremental,
        standalone=standalone,
        toc=toc,
        metadata=metadata,
        variable=variable,
        pdf_engine=pdf_engine,
        embed_resources=embed_resources,
    )

    result = run_pandoc(args, check=True, capture=True)

    if output == "-":
        if result.stdout:
            typer.echo(result.stdout, nl=False)
    else:
        report_success(output)
