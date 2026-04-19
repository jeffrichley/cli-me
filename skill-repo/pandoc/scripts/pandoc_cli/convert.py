"""convert command group — thin CLI dispatch.

Exposes `convert to INPUT OUTPUT [flags]` per the playbook contract. All
heavy lifting lives in `pandoc_cli.commands.convert_to`; this file just
wires Typer arguments through to `run_convert`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli import convert_app
from pandoc_cli.commands.convert_to import run_convert


@convert_app.command("to")
def cmd_to(
    input: Path = typer.Argument(..., help="Input file (path)"),
    output: str = typer.Argument(
        ...,
        help="Output file (use '-' for stdout — text formats only)",
    ),
    from_: Optional[str] = typer.Option(
        None,
        "--from",
        "-f",
        help="Override input format (e.g. markdown+yaml_metadata_block)",
    ),
    to: Optional[str] = typer.Option(
        None,
        "--to",
        "-t",
        help="Override output format (e.g. html5, latex, docx)",
    ),
    standalone: Optional[bool] = typer.Option(
        None,
        "--standalone/--no-standalone",
        help="Force standalone (full document) or fragment-only output",
    ),
    toc: bool = typer.Option(False, "--toc", help="Insert a table of contents"),
    toc_depth: Optional[int] = typer.Option(
        None, "--toc-depth", help="Number of heading levels to include in TOC"
    ),
    metadata: list[str] = typer.Option(
        [],
        "--metadata",
        "-M",
        help="Set document metadata as KEY=VALUE (repeatable)",
    ),
    pdf_engine: Optional[str] = typer.Option(
        None,
        "--pdf-engine",
        help="PDF engine: pdflatex, xelatex, lualatex, tectonic, weasyprint, ...",
    ),
    embed_resources: bool = typer.Option(
        False,
        "--embed-resources",
        help="Inline images / CSS / fonts (HTML output; implies --standalone)",
    ),
) -> None:
    """Convert INPUT to OUTPUT, dispatching to pandoc."""
    run_convert(
        str(input),
        output,
        from_=from_,
        to=to,
        standalone=standalone,
        toc=toc,
        toc_depth=toc_depth,
        metadata=list(metadata),
        pdf_engine=pdf_engine,
        embed_resources=embed_resources,
    )
