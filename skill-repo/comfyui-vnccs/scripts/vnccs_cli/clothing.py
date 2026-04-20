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
from vnccs_cli.commands import (
    clothing_add,
    clothing_list,
    clothing_pick,
    clothing_remove,
)

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
    state_dir: Annotated[
        Optional[str],
        typer.Option(
            "--state-dir",
            help="VNCCS state directory (overrides VNCCS_STATE_DIR env).",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a Rich table."),
    ] = False,
) -> None:
    """List costumes (and their variant counts) for one or all characters."""
    try:
        rows = clothing_list.run_list(character, comfy_path=path, state_dir=state_dir)
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


@app.command("add")
def add(
    character: Annotated[str, typer.Argument(help="Character name (must exist on disk).")],
    costume: Annotated[
        str,
        typer.Option("--name", help="New costume name (directory under Sheets/<character>/)."),
    ],
    description: Annotated[
        str,
        typer.Option(
            "--description",
            help="Clothing description. Routed to CharacterAssetSelector.top (most visible slot).",
        ),
    ],
    variants: Annotated[
        int,
        typer.Option("--variants", help="Number of variant submissions (each with a distinct seed)."),
    ] = 1,
    seed: Annotated[
        Optional[int],
        typer.Option(
            "--seed",
            help="Base seed; per-variant seeds are (base+0), (base+1)... If omitted, random.",
        ),
    ] = None,
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    state_dir: Annotated[
        Optional[str],
        typer.Option("--state-dir", help="VNCCS state directory (overrides VNCCS_STATE_DIR env)."),
    ] = None,
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Max seconds per variant submission."),
    ] = 600.0,
    wait: Annotated[
        bool,
        typer.Option("--wait/--no-wait", help="Poll /history until each variant finishes."),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of Rich summary."),
    ] = False,
) -> None:
    """Generate N clothing variants for CHARACTER (stage 2, SDXL legacy)."""
    try:
        result = clothing_add.run_add(
            character,
            costume,
            description,
            variants=variants,
            seed=seed,
            comfy_path=path,
            state_dir=state_dir,
            url=url,
            wait=wait,
            timeout=timeout,
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    _console.print(
        f"[bold cyan]{character}[/bold cyan] / [magenta]{costume}[/magenta] — "
        f"{variants} variant(s) submitted"
    )
    for sub in result["submissions"]:
        _console.print(
            f"  variant {sub['variant_index']} seed={sub['variant_seed']} "
            f"prompt_id=[green]{sub['prompt_id']}[/green]"
        )


@app.command("remove")
def remove(
    character: Annotated[str, typer.Argument(help="Character name (must exist).")],
    costume: Annotated[
        str,
        typer.Option("--name", help="Costume name to remove."),
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Required confirmation — this is destructive."),
    ] = False,
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    state_dir: Annotated[
        Optional[str],
        typer.Option("--state-dir", help="VNCCS state directory (overrides VNCCS_STATE_DIR env)."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON."),
    ] = False,
) -> None:
    """Delete a costume's Sheets/ tree + strip it from config. Requires --yes."""
    try:
        result = clothing_remove.run_remove(
            character,
            costume,
            confirm=yes,
            comfy_path=path,
            state_dir=state_dir,
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    r = result["removed"]
    suffix = " [dim](config updated)[/dim]" if result["config_updated"] else ""
    _console.print(
        f"[bold red]removed[/bold red] "
        f"[cyan]{character}[/cyan]/[magenta]{costume}[/magenta] "
        f"({r['file_count']} files, {r['total_bytes']:,} bytes){suffix}"
    )


@app.command("pick")
def pick(
    character: Annotated[str, typer.Argument(help="Character name.")],
    costume: Annotated[
        str,
        typer.Option("--name", help="Costume name."),
    ],
    variant: Annotated[
        int,
        typer.Option("--variant", help="Variant sequence number (NNNNN from sheet_neutral_NNNNN_.png)."),
    ],
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    state_dir: Annotated[
        Optional[str],
        typer.Option("--state-dir", help="VNCCS state directory (overrides VNCCS_STATE_DIR env)."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON."),
    ] = False,
) -> None:
    """Record the chosen variant for a costume in the character's config."""
    try:
        result = clothing_pick.run_pick(
            character,
            costume,
            variant,
            comfy_path=path,
            state_dir=state_dir,
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    _console.print(
        f"[bold green]picked[/bold green] "
        f"[cyan]{character}[/cyan]/[magenta]{costume}[/magenta] "
        f"variant=[yellow]{variant}[/yellow] "
        f"(available: {result['available_variants']})"
    )
