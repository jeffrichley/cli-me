"""character command group — stage 1 + 1.1 operations.

Implemented (Phase 3 Wave 1, read-only):
  @app.command("list")   — enumerate saved characters
  @app.command("show")   — inspect details + generated artifacts

Pending (Wave 2 / 3):
  @app.command("create") — generate character sheet from prompt (stage 1)
  @app.command("clone")  — derive from existing character (stage 1.1)
  @app.command("prune")  — delete a character and all derived data
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from vnccs_cli import backend
from vnccs_cli.backend import VnccsError
from vnccs_cli.commands import character_list, character_show

app = typer.Typer(
    help="Create / clone / list / inspect / prune VNCCS characters.",
    no_args_is_help=True,
)

_console = Console()


@app.command("list")
def list_(
    path: Annotated[
        Optional[str],
        typer.Option(
            "--path",
            help="ComfyUI install directory (overrides COMFY_PATH env).",
        ),
    ] = None,
    state_dir: Annotated[
        Optional[str],
        typer.Option(
            "--state-dir",
            help=(
                "VNCCS character state directory (overrides "
                "VNCCS_STATE_DIR env; default <COMFY_PATH>/output/VN_CharacterCreatorSuit)."
            ),
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a Rich table."),
    ] = False,
) -> None:
    """List VNCCS characters under the configured state directory."""
    try:
        characters = character_list.run_list(comfy_path=path, state_dir=state_dir)
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(characters, indent=2))
        return

    if not characters:
        _console.print("No characters found")
        return

    table = Table(title=f"Characters ({len(characters)})")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Costumes", justify="right")
    table.add_column("Emotions", justify="right")
    table.add_column("Last Modified")
    for c in characters:
        table.add_row(
            c["name"],
            c["path"],
            str(c["costume_count"]),
            str(c["emotion_count"]),
            c["last_modified"],
        )
    _console.print(table)


@app.command("show")
def show(
    name: Annotated[str, typer.Argument(help="Character name (directory name under the VNCCS state dir).")],
    path: Annotated[
        Optional[str],
        typer.Option(
            "--path",
            help="ComfyUI install directory (overrides COMFY_PATH env).",
        ),
    ] = None,
    state_dir: Annotated[
        Optional[str],
        typer.Option(
            "--state-dir",
            help="VNCCS character state directory (overrides VNCCS_STATE_DIR env).",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a Rich summary."),
    ] = False,
) -> None:
    """Inspect one character's full on-disk artifact tree."""
    try:
        record = character_show.run_show(
            name, comfy_path=path, state_dir=state_dir
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(record, indent=2))
        return

    _render_show_rich(record)


def _render_show_rich(record: dict) -> None:
    """Render the `character show` record as a set of Rich tables."""
    _console.print(f"[bold cyan]{record['name']}[/bold cyan]")
    _console.print(f"[dim]{record['state_path']}[/dim]")

    cfg = record["config"]
    cfg_status = "[green]present[/green]" if cfg["present"] else "[yellow]absent[/yellow]"
    _console.print(f"config.json: {cfg_status} ({cfg['path']})")

    sheet = record["character_sheet"]
    if sheet["present"]:
        _console.print(
            f"character sheet: [green]present[/green] "
            f"({sheet['size']:,} bytes) {sheet['path']}"
        )
    else:
        _console.print("character sheet: [yellow]absent[/yellow]")

    costumes = record["costumes"]
    c_table = Table(title=f"Costumes ({len(costumes)})")
    c_table.add_column("Name", style="cyan")
    c_table.add_column("Variants", justify="right")
    c_table.add_column("Picked Variant")
    for c in costumes:
        c_table.add_row(
            c["name"],
            str(c["variant_count"]),
            "" if c["picked_variant"] is None else str(c["picked_variant"]),
        )
    _console.print(c_table)

    emotions = record["emotions"]
    e_table = Table(title=f"Emotions ({len(emotions)})")
    e_table.add_column("Costume", style="cyan")
    e_table.add_column("Emotion")
    e_table.add_column("Path", style="dim")
    for e in emotions:
        e_table.add_row(e["costume"], e["emotion_type"], e["path"])
    _console.print(e_table)

    sprites = record["sprites"]
    _console.print(
        f"sprites: {'[green]exists[/green]' if sprites['exists'] else '[yellow]absent[/yellow]'} "
        f"({sprites['png_count']} PNGs) {sprites['path']}"
    )

    ds = record["dataset"]
    _console.print(
        f"dataset (lora/): "
        f"{'[green]exists[/green]' if ds['exists'] else '[yellow]absent[/yellow]'} "
        f"({ds['row_count']} rows) {ds['path']}"
    )
