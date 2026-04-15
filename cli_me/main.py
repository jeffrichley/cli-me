"""cli-me: Agent-native skills for GUI software."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from cli_me.installer import Installer
from cli_me.registry import Registry

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="clime",
    help="Agent-native skills for GUI software — build, install, and evolve Claude Code skills.",
    no_args_is_help=True,
)


def _find_skill_repo() -> Path:
    """Locate the skill-repo directory."""
    env = os.environ.get("CLIME_SKILL_REPO")
    if env:
        return Path(env)
    # Default: skill-repo/ relative to this package's repo root
    return Path(__file__).resolve().parent.parent / "skill-repo"


def _get_registry() -> Registry:
    repo = _find_skill_repo()
    return Registry(repo / "registry.json")


def _get_installer() -> Installer:
    return Installer(_find_skill_repo())


@app.command()
def list(
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
) -> None:
    """List available skills in the skill-repo."""
    reg = _get_registry()
    if category:
        skills = reg.list_by_category(category)
    else:
        skills = reg.list_all()

    if not skills:
        console.print("No skills found.", style="dim")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Tags")
    for skill in skills:
        tags = ", ".join(skill.get("tags", []))
        table.add_row(skill["name"], skill.get("category", ""), tags)
    console.print(table)


@app.command()
def search(query: str = typer.Argument(..., help="Search query")) -> None:
    """Search skills by name, description, or tags."""
    reg = _get_registry()
    results = reg.search(query)
    if not results:
        console.print("No skills found matching query.", style="dim")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Description")
    for skill in results:
        table.add_row(skill["name"], skill.get("description", ""))
    console.print(table)


@app.command()
def info(name: str = typer.Argument(..., help="Skill name")) -> None:
    """Show detailed information about a skill."""
    reg = _get_registry()
    skill = reg.get(name)
    if skill is None:
        err_console.print(f"Skill '{name}' not found.", style="bold red")
        raise typer.Exit(code=1)

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Name", skill["name"])
    table.add_row("Description", skill.get("description", ""))
    table.add_row("Category", skill.get("category", ""))
    table.add_row("Tags", ", ".join(skill.get("tags", [])))
    table.add_row("Version", skill.get("version", ""))
    table.add_row("Software", skill.get("software_url", ""))
    table.add_row("Source", skill.get("source_repo", ""))
    deps = skill.get("dependencies", [])
    if deps:
        table.add_row("Dependencies", ", ".join(deps))
    console.print(table)


@app.command()
def install(
    name: str = typer.Argument(..., help="Skill name to install"),
    project: str = typer.Option(None, "--project", "-p", help="Project directory"),
    global_: bool = typer.Option(False, "--global", "-g", help="Install globally"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing"),
) -> None:
    """Install a skill to a project or globally."""
    if not project and not global_:
        err_console.print("Specify --project <path> or --global.", style="bold red")
        raise typer.Exit(code=1)

    installer = _get_installer()
    try:
        dest = installer.install(
            name,
            project_path=project,
            global_install=global_,
            force=force,
        )
        console.print(f"Installed [bold]{name}[/bold] to {dest}", style="green")
    except (ValueError, FileExistsError) as e:
        err_console.print(str(e), style="bold red")
        raise typer.Exit(code=1)


@app.command()
def uninstall(
    name: str = typer.Argument(..., help="Skill name to uninstall"),
    project: str = typer.Option(None, "--project", "-p", help="Project directory"),
    global_: bool = typer.Option(False, "--global", "-g", help="Uninstall globally"),
) -> None:
    """Uninstall a skill from a project or globally."""
    if not project and not global_:
        err_console.print("Specify --project <path> or --global.", style="bold red")
        raise typer.Exit(code=1)

    installer = _get_installer()
    try:
        installer.uninstall(name, project_path=project, global_install=global_)
        console.print(f"Uninstalled [bold]{name}[/bold].", style="green")
    except FileNotFoundError as e:
        err_console.print(str(e), style="bold red")
        raise typer.Exit(code=1)


def main() -> None:
    app()
