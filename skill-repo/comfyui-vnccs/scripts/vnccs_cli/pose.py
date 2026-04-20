"""pose command group — enumerate bundled pose presets.

`list` walks `<VNCCS>/presets/poses/` and prints filename + size per
image preset. Pure filesystem — no HTTP.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from vnccs_cli import backend
from vnccs_cli.backend import VnccsError
from vnccs_cli.commands import pose_list

app = typer.Typer(
    help="List pose presets from the installed VNCCS node pack's presets/poses/ directory.",
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
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a Rich table."),
    ] = False,
) -> None:
    """Enumerate pose preset images from <VNCCS>/presets/poses/."""
    try:
        poses = pose_list.run_list(comfy_path=path)
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(poses, indent=2))
        return

    if not poses:
        _console.print("No poses found")
        return

    table = Table(title=f"Pose presets ({len(poses)})")
    table.add_column("Filename", style="cyan")
    table.add_column("Size", justify="right")
    for pose in poses:
        table.add_row(pose["name"], _format_size(pose["size"]))
    _console.print(table)
