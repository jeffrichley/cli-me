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
from vnccs_cli.commands import (
    character_clone,
    character_create,
    character_list,
    character_show,
)

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


@app.command("create")
def create(
    name: Annotated[str, typer.Argument(help="New character name (becomes the directory under the VNCCS state dir).")],
    description: Annotated[
        str,
        typer.Option(
            "--description",
            help="Freeform character description. Routed to CharacterCreator.additional_details.",
        ),
    ],
    pose: Annotated[
        Optional[str],
        typer.Option(
            "--pose",
            help="Pose preset filename (without .png). Enumerate with `vnccs pose list`.",
        ),
    ] = None,
    seed: Annotated[
        Optional[int],
        typer.Option("--seed", help="Override the workflow's seed (default leaves it untouched)."),
    ] = None,
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Max seconds to wait for the prompt to complete."),
    ] = 600.0,
    wait: Annotated[
        bool,
        typer.Option("--wait/--no-wait", help="Poll /history until the prompt finishes (default)."),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of Rich table."),
    ] = False,
) -> None:
    """Generate a new character sheet from a prompt (stage 1, SDXL legacy)."""
    try:
        result = character_create.run_create(
            name,
            description,
            pose=pose,
            seed=seed,
            url=url,
            wait=wait,
            timeout=timeout,
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    _console.print(f"[bold cyan]{name}[/bold cyan] submitted")
    _console.print(f"prompt_id: [green]{result['prompt_id']}[/green]")
    if wait:
        _console.print("[green]finished[/green]")


@app.command("clone")
def clone(
    name: Annotated[str, typer.Argument(help="New (derived) character name.")],
    from_: Annotated[
        str,
        typer.Option(
            "--from",
            help="Existing source character name. Must already exist under the state dir.",
        ),
    ],
    prompt: Annotated[
        Optional[str],
        typer.Option(
            "--prompt",
            help="Optional override description. Routed to CharacterCreator.additional_details.",
        ),
    ] = None,
    seed: Annotated[
        Optional[int],
        typer.Option("--seed", help="Override the workflow's seed."),
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
        typer.Option("--timeout", help="Max seconds to wait for the prompt."),
    ] = 600.0,
    wait: Annotated[
        bool,
        typer.Option("--wait/--no-wait", help="Poll /history until finished."),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON."),
    ] = False,
) -> None:
    """Derive a new character from an existing one (stage 1.1, QWEN clone)."""
    try:
        result = character_clone.run_clone(
            name,
            from_,
            prompt=prompt,
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
    _console.print(f"[bold cyan]{name}[/bold cyan] cloned from [dim]{from_}[/dim]")
    _console.print(f"prompt_id: [green]{result['prompt_id']}[/green]")
