"""config command group — introspect resolved paths and URL.

`show` prints the resolved ComfyUI install path, ComfyUI base URL, VNCCS
node pack install dir, detected VNCCS version, bundled workflow dir, and
models / output roots. Pure filesystem — no HTTP.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from vnccs_cli import backend
from vnccs_cli.backend import VnccsError
from vnccs_cli.commands import config_show

app = typer.Typer(
    help="Show resolved VNCCS CLI configuration (paths, URLs).",
    no_args_is_help=True,
)

_console = Console()

# Human-readable labels for each key in the config dict. Declared once so
# the table renderer and any docs stay in sync. Order here is the order
# the table displays the fields in.
_FIELD_LABELS: list[tuple[str, str]] = [
    ("comfy_path", "COMFY_PATH"),
    ("comfy_url", "COMFY_URL"),
    ("vnccs_install_dir", "VNCCS install dir"),
    ("vnccs_version", "VNCCS version"),
    ("bundled_workflow_dir", "Bundled workflow dir"),
    ("models_root", "Models root"),
    ("vnccs_state_dir", "VNCCS state dir"),
]


@app.command("show")
def show(
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a Rich table."),
    ] = False,
) -> None:
    """Print resolved COMFY_PATH, COMFY_URL, VNCCS install dir, and related paths."""
    try:
        cfg = config_show.run_show(comfy_path=path, url=url)
    except VnccsError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(cfg, indent=2))
        return

    table = Table(title="VNCCS CLI configuration", show_header=False, title_style="bold")
    table.add_column("Field", style="dim")
    table.add_column("Value")
    for key, label in _FIELD_LABELS:
        table.add_row(label, cfg[key])
    _console.print(table)
