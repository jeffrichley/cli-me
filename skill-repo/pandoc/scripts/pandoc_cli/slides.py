"""slides command group — thin CLI dispatch for pandoc slide decks."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli import slides_app


@slides_app.command("build")
def cmd_build(
    input: Path = typer.Argument(..., help="Input markdown file"),
    output: str = typer.Argument(
        ...,
        help="Output file ('-' allowed for revealjs only)",
    ),
    to: str = typer.Option(
        ...,
        "--to",
        help="Slide writer: beamer or revealjs",
    ),
    from_: Optional[str] = typer.Option(
        None,
        "--from",
        "-f",
        help="Override input format (e.g. markdown+yaml_metadata_block)",
    ),
    slide_level: Optional[int] = typer.Option(
        None,
        "--slide-level",
        help="Heading level that starts a new slide",
    ),
    incremental: bool = typer.Option(
        False,
        "--incremental",
        "-i",
        help="Make lists display incrementally",
    ),
    standalone: Optional[bool] = typer.Option(
        None,
        "--standalone/--no-standalone",
        help="Force standalone slide output or fragment-only output",
    ),
    toc: bool = typer.Option(False, "--toc", help="Insert a table of contents"),
    metadata: list[str] = typer.Option(
        [],
        "--metadata",
        "-M",
        help="Set document metadata as KEY=VALUE (repeatable)",
    ),
    variable: list[str] = typer.Option(
        [],
        "--variable",
        "-V",
        help="Set writer/template variable as KEY=VALUE (repeatable)",
    ),
    pdf_engine: Optional[str] = typer.Option(
        None,
        "--pdf-engine",
        help="PDF engine for beamer PDF output",
    ),
    embed_resources: bool = typer.Option(
        False,
        "--embed-resources",
        help="Inline linked assets for revealjs HTML output",
    ),
) -> None:
    """Build a slide deck using the beamer or revealjs writer."""
    from pandoc_cli.commands.slides_build import run_build

    run_build(
        str(input),
        output,
        to=to,
        from_=from_,
        slide_level=slide_level,
        incremental=incremental,
        standalone=standalone,
        toc=toc,
        metadata=list(metadata),
        variable=list(variable),
        pdf_engine=pdf_engine,
        embed_resources=embed_resources,
    )
