"""citations command group — thin CLI dispatch.

All real logic lives in `pandoc_cli.commands.citations_render`. This module
just wires Typer's argument parsing to that logic. See the docstring of
`commands/citations_render.py` for the design rationale (why `--natbib` and
`--biblatex` are not exposed here).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pandoc_cli import citations_app
from pandoc_cli.commands.citations_render import run_render


@citations_app.command("render")
def citations_render(
    input: Path = typer.Argument(..., help="Input document (markdown, etc.)"),
    output: Path = typer.Argument(..., help="Output document (extension drives format)"),
    bibliography: Path = typer.Option(
        ...,
        "--bibliography",
        "-b",
        help="Bibliography file (.bib, .bibtex, .json, .yaml, .ris)",
    ),
    csl: Optional[Path] = typer.Option(
        None,
        "--csl",
        help="CSL style file (default: chicago-author-date)",
    ),
    from_: Optional[str] = typer.Option(
        None,
        "--from",
        "-f",
        help="Input format (passed verbatim to pandoc, e.g. markdown+yaml_metadata_block)",
    ),
    to: Optional[str] = typer.Option(
        None,
        "--to",
        "-t",
        help="Output format (passed verbatim to pandoc, e.g. html5)",
    ),
    standalone: Optional[bool] = typer.Option(
        None,
        "--standalone/--no-standalone",
        help="Force standalone document mode (default: pandoc decides)",
    ),
    metadata: Optional[list[str]] = typer.Option(
        None,
        "--metadata",
        "-M",
        help="Metadata KEY=VALUE pairs forwarded to pandoc (repeatable)",
    ),
) -> None:
    """Render a document with citations resolved via --citeproc.

    Always passes --citeproc and --bibliography. Optionally forwards --csl,
    --from / --to, --standalone, and repeated --metadata. natbib / biblatex
    rendering is intentionally not supported by this subcommand — see the
    citations technique page for the rationale.
    """
    run_render(
        str(input),
        str(output),
        str(bibliography),
        csl=str(csl) if csl is not None else None,
        from_=from_,
        to=to,
        standalone=standalone,
        metadata=list(metadata) if metadata else None,
    )
