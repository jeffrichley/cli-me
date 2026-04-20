"""emotion command group — stage 3 operations (emotion sheets per character/costume).

Wave 1 (this file, read-only):
  @app.command("list")    — enumerate (costume, emotion) pairs for a character
  @app.command("show")    — inspect one emotion sheet (path, size, mtime)
  @app.command("preview") — show the bundled reference image for an emotion

Wave 2 (Phase 3.2):
  @app.command("add") — generate emotion sheet (defaults to --legacy SDXL;
                        --qwen opts into broken upstream QWEN path)

Upstream bug note (see references/gotchas.md): VNCCS 2.1.0's QWEN emotion
workflow references VNCCS_QWEN_Detailer and VNCCS_BBox_Extractor which are
not registered in any published branch. `--legacy` uses the working SDXL
workflow (V1SDXL/) and is the default until upstream ships the missing
Python classes.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from vnccs_cli import backend
from vnccs_cli.backend import VnccsError
from vnccs_cli.commands import emotion_list, emotion_preview, emotion_show

app = typer.Typer(
    help="Add / list / show / preview emotion sheets for VNCCS characters.",
    no_args_is_help=True,
)

_console = Console()


def _format_size(n: int) -> str:
    """Human-readable byte count: '512 B', '14.2 KiB', '3.1 MiB'."""
    if n < 1024:
        return f"{n} B"
    kib = n / 1024
    if kib < 1024:
        return f"{kib:.1f} KiB"
    return f"{kib / 1024:.1f} MiB"


@app.command("list")
def list_(
    character: Annotated[
        str,
        typer.Argument(help="Character name (directory under VN_CharacterCreatorSuit/)."),
    ],
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
    """List every (costume, emotion) pair that has at least one rendered sheet."""
    try:
        rows = emotion_list.run_list(character, comfy_path=path, state_dir=state_dir)
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(rows, indent=2))
        return

    if not rows:
        _console.print("No costumes found")
        return

    table = Table(title=f"Emotions for {character} ({len(rows)})")
    table.add_column("Costume", style="cyan")
    table.add_column("Emotion", style="magenta")
    table.add_column("Path", overflow="fold")
    for row in rows:
        table.add_row(row["costume"], row["emotion"], row["path"])
    _console.print(table)


@app.command("show")
def show(
    character: Annotated[
        str,
        typer.Argument(help="Character name."),
    ],
    emotion: Annotated[
        str,
        typer.Option("--emotion", help="Emotion type (e.g. 'happy', 'radiant-smile')."),
    ],
    costume: Annotated[
        Optional[str],
        typer.Option("--costume", help="Costume name (required if the emotion exists in multiple costumes)."),
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
    """Inspect the latest rendered sheet for one emotion (path, size, mtime)."""
    try:
        info = emotion_show.run_show(
            character,
            emotion=emotion,
            costume=costume,
            comfy_path=path,
            state_dir=state_dir,
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(info, indent=2))
        return

    table = Table(
        title=f"Emotion: {info['character']} / {info['costume']} / {info['emotion']}",
        show_header=False,
        title_style="bold",
    )
    table.add_column("Field", style="dim")
    table.add_column("Value", overflow="fold")
    table.add_row("Character", info["character"])
    table.add_row("Costume", info["costume"])
    table.add_row("Emotion", info["emotion"])
    table.add_row("Path", info["path"])
    table.add_row("Size", _format_size(info["size"]))
    table.add_row("Created", info["created"])
    _console.print(table)


@app.command("preview")
def preview(
    character: Annotated[
        str,
        typer.Argument(help="Character name (validated; doesn't affect the bundled preview)."),
    ],
    emotion: Annotated[
        str,
        typer.Option("--emotion", help="Bundled emotion safe_name (e.g. 'angry', 'radiant-smile')."),
    ],
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
        typer.Option("--json", help="Emit JSON instead of plain-text path."),
    ] = False,
) -> None:
    """Show the bundled pre-rendered reference image for EMOTION."""
    try:
        info = emotion_preview.run_preview(
            character,
            emotion=emotion,
            comfy_path=path,
            state_dir=state_dir,
        )
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(info, indent=2))
        return

    # Non-JSON: just print the path. Parseable by shell tools; Rich would
    # needlessly wrap a single absolute path on narrow terminals.
    typer.echo(info["path"])
