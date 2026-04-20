"""custom-nodes group — install / list / update / remove ComfyUI custom node packs.

ComfyUI loads any subdirectory of `<ComfyUI>/custom_nodes/` as a node pack
on startup (no hot-reload). This group lets agents manage that directory
without leaving the cli.

ComfyUI install path is required for every command — pass --path or set
COMFY_PATH. The Python interpreter that runs ComfyUI (used to pip install
custom-node requirements) is auto-detected next to COMFY_PATH (.venv,
python_embeded), or override with --python / COMFY_PYTHON.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from comfyui_cli import backend
from comfyui_cli.backend import ComfyError
from comfyui_cli.commands import (
    custom_nodes_install,
    custom_nodes_list,
    custom_nodes_remove,
    custom_nodes_update,
)

app = typer.Typer(
    help="Install / list / update / remove ComfyUI custom node packs.",
    no_args_is_help=True,
)

_console = Console()


@app.command("install")
def install(
    repo_url: Annotated[str, typer.Argument(help="Git URL of the custom node repo (https or ssh).")],
    name: Annotated[
        Optional[str],
        typer.Option("--name", help="Override the install directory name (default: derived from URL)."),
    ] = None,
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    python: Annotated[
        Optional[str],
        typer.Option(
            "--python",
            help="Python interpreter for installing requirements.txt (overrides COMFY_PYTHON / auto-detect).",
        ),
    ] = None,
    no_deps: Annotated[
        bool,
        typer.Option("--no-deps", help="Skip `pip install -r requirements.txt` after cloning."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Re-clone if the directory already exists (deletes existing)."),
    ] = False,
) -> None:
    """Clone REPO_URL into <ComfyUI>/custom_nodes/ and install its requirements."""
    try:
        result = custom_nodes_install.run_install(
            repo_url,
            name=name,
            comfy_path=path,
            python_path=python,
            no_deps=no_deps,
            force=force,
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)

    if result.get("skipped"):
        _console.print(f"[yellow]skipped:[/yellow] {result['name']} — {result['reason']}")
        return
    _console.print(f"[green]installed:[/green] {result['name']} -> {result['path']}")
    if result["deps_installed"]:
        _console.print("  requirements.txt installed")
    if result.get("restart_required"):
        _console.print(
            "[bold]restart ComfyUI[/bold] for the new custom node to load."
        )


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
    """List custom node packs installed under <ComfyUI>/custom_nodes/."""
    try:
        nodes = custom_nodes_list.run_list(comfy_path=path)
    except ComfyError as err:
        backend.print_error_and_exit(err)

    if json_output:
        typer.echo(json.dumps(nodes, indent=2))
        return

    if not nodes:
        _console.print("(no custom nodes installed)")
        return

    table = Table(title=f"Custom nodes ({len(nodes)})")
    table.add_column("Name", style="cyan")
    table.add_column("Git", style="green")
    table.add_column("Branch")
    table.add_column("Commit")
    table.add_column("Reqs", style="yellow")
    table.add_column("Remote", style="dim")
    for n in nodes:
        table.add_row(
            n["name"],
            "yes" if n["is_git"] else "no",
            n.get("branch", ""),
            n.get("commit", ""),
            "yes" if n["has_requirements"] else "",
            n.get("remote", ""),
        )
    _console.print(table)


@app.command("update")
def update(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Custom node name to update (omit with --all)."),
    ] = None,
    all_nodes: Annotated[
        bool,
        typer.Option("--all", help="Update every git-tracked custom node."),
    ] = False,
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    python: Annotated[
        Optional[str],
        typer.Option(
            "--python",
            help="Python interpreter for reinstalling requirements.txt (overrides COMFY_PYTHON / auto-detect).",
        ),
    ] = None,
    no_deps: Annotated[
        bool,
        typer.Option("--no-deps", help="Skip `pip install -r requirements.txt` after pulling."),
    ] = False,
) -> None:
    """Run `git pull` (and reinstall requirements) on one or all custom nodes."""
    try:
        results = custom_nodes_update.run_update(
            name,
            all_nodes=all_nodes,
            comfy_path=path,
            python_path=python,
            no_deps=no_deps,
        )
    except ComfyError as err:
        backend.print_error_and_exit(err)

    if not results:
        _console.print("(no git-tracked custom nodes to update)")
        return

    for r in results:
        if "error" in r:
            _console.print(f"[red]failed:[/red] {r['name']} — {r['error']}")
            if r.get("detail"):
                _console.print(f"  [dim]{r['detail']}[/dim]")
            continue
        marker = "[dim]up to date[/dim]" if r["already_up_to_date"] else "[green]updated[/green]"
        _console.print(f"{marker}: {r['name']}")
        if r["deps_installed"]:
            _console.print("  requirements.txt reinstalled")


@app.command("remove")
def remove(
    name: Annotated[str, typer.Argument(help="Custom node name to remove.")],
    path: Annotated[
        Optional[str],
        typer.Option("--path", help="ComfyUI install directory (overrides COMFY_PATH env)."),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm deletion (required — protects against typos)."),
    ] = False,
) -> None:
    """Delete <ComfyUI>/custom_nodes/NAME. Requires --yes."""
    try:
        result = custom_nodes_remove.run_remove(name, comfy_path=path, yes=yes)
    except ComfyError as err:
        backend.print_error_and_exit(err)

    _console.print(f"[red]removed:[/red] {result['name']} ({result['path']})")
    if result.get("restart_required"):
        _console.print(
            "[bold]restart ComfyUI[/bold] to clear the removed node from memory."
        )
