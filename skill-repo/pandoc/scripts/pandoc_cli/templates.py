"""templates command group — thin CLI dispatch.

Exposes three commands per the playbook contract:
  * ``templates print FORMAT`` — emit pandoc's default template for FORMAT.
  * ``templates apply INPUT OUTPUT --template T`` — convert with --template.
  * ``templates eisvogel INPUT OUTPUT`` — PDF using bundled Eisvogel.

All heavy lifting lives in ``pandoc_cli.commands.templates_*``; this file
only wires Typer arguments through to the corresponding ``run_*`` function.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli import templates_app
from pandoc_cli.commands.templates_apply import run_apply
from pandoc_cli.commands.templates_eisvogel import run_eisvogel
from pandoc_cli.commands.templates_print import run_print


@templates_app.command("print")
def cmd_print(
    format: str = typer.Argument(
        ...,
        help="Pandoc writer name (e.g. latex, html5, revealjs, markdown)",
    ),
) -> None:
    """Print pandoc's default template for FORMAT to stdout."""
    text = run_print(format)
    # Use typer.echo with nl=False so we don't double-newline what pandoc
    # already terminated; templates always end with a trailing newline.
    typer.echo(text, nl=False)


@templates_app.command("apply")
def cmd_apply(
    input: Path = typer.Argument(..., help="Input file (path)"),
    output: str = typer.Argument(..., help="Output file"),
    template: Path = typer.Option(
        ...,
        "--template",
        help="Path to the template file (LaTeX, HTML, Markdown, RTF, ...)",
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
        help="Override output format (e.g. html5, latex)",
    ),
    variable: list[str] = typer.Option(
        [],
        "--variable",
        "-V",
        help="Set template variable as KEY=VALUE (repeatable)",
    ),
    metadata: list[str] = typer.Option(
        [],
        "--metadata",
        "-M",
        help="Set document metadata as KEY=VALUE (repeatable)",
    ),
) -> None:
    """Convert INPUT to OUTPUT using the given --template."""
    run_apply(
        str(input),
        output,
        str(template),
        from_=from_,
        to=to,
        variable=list(variable),
        metadata=list(metadata),
    )


@templates_app.command("eisvogel")
def cmd_eisvogel(
    input: Path = typer.Argument(..., help="Input markdown file"),
    output: str = typer.Argument(..., help="Output PDF file (.pdf recommended)"),
    toc: bool = typer.Option(False, "--toc", help="Insert a table of contents"),
    variable: list[str] = typer.Option(
        [],
        "--variable",
        "-V",
        help="Set Eisvogel template variable as KEY=VALUE (e.g. titlepage=true)",
    ),
    pdf_engine: Optional[str] = typer.Option(
        None,
        "--pdf-engine",
        help="LaTeX engine: xelatex (default if available), pdflatex, lualatex, ...",
    ),
) -> None:
    """Convert INPUT to a styled PDF using the bundled Eisvogel template."""
    run_eisvogel(
        str(input),
        output,
        toc=toc,
        variable=list(variable),
        pdf_engine=pdf_engine,
    )
