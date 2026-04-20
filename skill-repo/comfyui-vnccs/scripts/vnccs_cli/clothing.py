"""clothing command group — stage 2 operations (costume sets per character).

Wave 1 (this file, read-only):
  @app.command("list")   — enumerate costumes (optionally per character)

Wave 2 (Phase 3.2, submission + destructive):
  @app.command("add")    — generate N clothing variants for a character
  @app.command("remove") — delete a costume set
  @app.command("pick")   — pick one variant from a multi-variant costume
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from vnccs_cli import backend
from vnccs_cli.backend import VnccsError
from vnccs_cli.commands import clothing_list

app = typer.Typer(
    help="Add / list / remove / pick clothing variants per VNCCS character.",
    no_args_is_help=True,
)

_console = Console()


def _render_picked(picked: Optional[int]) -> str:
    """Picked-variant column text: the sequence int or a dash placeholder."""
    return str(picked) if picked is not None else "—"


@app.command("list")
def list_(
    character: Annotated[
        Optional[str],
        typer.Argument(
            help="Character name. If omitted, list costumes for every character.",
        ),
    ] = None,
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a Rich table."),
    ] = False,
) -> None:
    """List costumes (and their variant counts) for one or all characters."""
    try:
        rows = clothing_list.run_list(character, comfy_path=path)
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(rows, indent=2))
        return

    if not rows:
        _console.print("No costumes found")
        return

    title = (
        f"Costumes for {character} ({len(rows)})"
        if character is not None
        else f"Costumes across all characters ({len(rows)})"
    )
    table = Table(title=title)
    table.add_column("Character", style="cyan")
    table.add_column("Costume", style="magenta")
    table.add_column("Variants", justify="right")
    table.add_column("Picked", justify="right")
    for row in rows:
        table.add_row(
            row["character"],
            row["costume"],
            str(row["variant_count"]),
            _render_picked(row["picked_variant"]),
        )
    _console.print(table)
