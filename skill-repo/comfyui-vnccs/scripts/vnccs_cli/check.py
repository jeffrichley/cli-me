"""check command group — verify VNCCS + custom nodes + models + server.

Thin Typer wrapper. Logic lives in commands/check_*.py so it can be
tested without instantiating Typer apps.

Commands:
  nodes  — verify every pack in REQUIRED_CUSTOM_NODE_PACKS
  models — cross-reference REQUIRED_MODELS vs files on disk
  all    — run nodes + models + server ping (exit 0 only if all green)
"""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from vnccs_cli import backend
from vnccs_cli.backend import VnccsError
from vnccs_cli.commands.check_all import run_check_all
from vnccs_cli.commands.check_models import run_check_models
from vnccs_cli.commands.check_nodes import run_check_nodes

app = typer.Typer(
    help="Verify VNCCS + custom nodes + models + server reachability.",
    no_args_is_help=True,
)

_console = Console()


# --- rendering helpers ------------------------------------------------------


def _render_nodes_table(rows: list[dict]) -> Table:
    """Build a Rich table for the `check nodes` report."""
    table = Table(title="VNCCS required custom-node packs", show_lines=False)
    table.add_column("Pack", style="bold")
    table.add_column("Present")
    table.add_column("Path", overflow="fold")
    for row in rows:
        present_cell = (
            "[green]yes[/green]" if row["present"] else f"[red]no[/red] ({row['reason']})"
        )
        table.add_row(row["name"], present_cell, row["path"])
    return table


def _render_models_table(rows: list[dict]) -> Table:
    """Build a Rich table for the `check models` report.

    When a model is missing, the download URL appears in the last column.
    Optional models are annotated so the user knows their absence is a
    warning, not a failure.
    """
    table = Table(title="VNCCS required models", show_lines=False)
    table.add_column("Filename", style="bold", overflow="fold")
    table.add_column("Type")
    table.add_column("Target dir")
    table.add_column("Present")
    table.add_column("Download URL (if missing)", overflow="fold")
    for row in rows:
        if row["present"]:
            present_cell = "[green]yes[/green]"
            url_cell = ""
        elif row["optional"]:
            present_cell = "[yellow]no (optional)[/yellow]"
            url_cell = row["download_url"]
        else:
            present_cell = "[red]no[/red]"
            url_cell = row["download_url"]
        table.add_row(
            row["filename"], row["type"], row["subdir"], present_cell, url_cell
        )
    return table


def _render_server_row(server: dict) -> str:
    """One-liner summary for server reachability."""
    if server["reachable"]:
        return f"ComfyUI at {server['url']}: [green]reachable[/green] ({server['detail']})"
    return (
        f"ComfyUI at {server['url']}: [red]unreachable[/red] — {server['detail']}"
    )


# --- commands ---------------------------------------------------------------


@app.command("nodes")
def nodes(
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install dir (overrides COMFY_PATH env)."),
    ] = None,
) -> None:
    """Verify every required custom-node pack is installed under custom_nodes/.

    Exit 0 if all packs present; exit 5 if any pack is missing; exit 6 if
    COMFY_PATH is unset or not a ComfyUI install.
    """
    try:
        rows = run_check_nodes(comfy_path=path)
    except VnccsError as err:
        backend.print_error_and_exit(err)
        return  # unreachable — kept for static analysers

    _console.print(_render_nodes_table(rows))

    missing = [r for r in rows if not r["present"]]
    if missing:
        _console.print(
            f"[red]{len(missing)} of {len(rows)} required packs missing.[/red]"
        )
        raise typer.Exit(code=5)
    _console.print(f"[green]all {len(rows)} required packs present.[/green]")


@app.command("models")
def models(
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install dir (overrides COMFY_PATH env)."),
    ] = None,
) -> None:
    """Verify every required model file is present under models/.

    Exit 0 if all required models present (optional ones may be missing
    with a warning); exit 5 if any required model is missing; exit 6 if
    COMFY_PATH is unset or not a ComfyUI install.
    """
    try:
        rows = run_check_models(comfy_path=path)
    except VnccsError as err:
        backend.print_error_and_exit(err)
        return  # unreachable

    _console.print(_render_models_table(rows))

    missing_required = [r for r in rows if not r["present"] and not r["optional"]]
    missing_optional = [r for r in rows if not r["present"] and r["optional"]]

    if missing_optional:
        _console.print(
            f"[yellow]{len(missing_optional)} optional models missing "
            "(auto-downloaded on first use).[/yellow]"
        )

    if missing_required:
        _console.print(
            f"[red]{len(missing_required)} required models missing.[/red]"
        )
        raise typer.Exit(code=5)
    _console.print("[green]all required models present.[/green]")


@app.command("all")
def all_(
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install dir (overrides COMFY_PATH env)."),
    ] = None,
    url: Annotated[
        Optional[str],
        typer.Option("--url", help="ComfyUI base URL (overrides COMFY_URL env)."),
    ] = None,
) -> None:
    """Run nodes + models + server reachability checks and aggregate exit code.

    Exit 0 only if every required pack, every required model, AND the
    ComfyUI server all pass. Exit 5 if any check fails; exit 6 if
    COMFY_PATH is unset or not a ComfyUI install.
    """
    try:
        report = run_check_all(comfy_path=path, comfy_url=url)
    except VnccsError as err:
        backend.print_error_and_exit(err)
        return  # unreachable

    _console.print(_render_nodes_table(report["nodes"]))
    _console.print(_render_models_table(report["models"]))
    _console.print(_render_server_row(report["server"]))

    if report["ok"]:
        _console.print("[green]check all: PASS[/green]")
        return

    # Summarize what failed so the user can jump to the right sub-command.
    failed_bits: list[str] = []
    if not all(r["present"] for r in report["nodes"]):
        failed_bits.append("nodes")
    if not all(r["present"] for r in report["models"] if not r["optional"]):
        failed_bits.append("models")
    if not report["server"]["reachable"]:
        failed_bits.append("server")
    _console.print(
        f"[red]check all: FAIL ({', '.join(failed_bits)})[/red]"
    )
    raise typer.Exit(code=5)
