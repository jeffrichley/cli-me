"""cli-me: Agent-native skills for GUI software."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from cli_me.installer import Installer
from cli_me.registry import Registry

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
        typer.echo("No skills found.")
        return

    for skill in skills:
        tags = ", ".join(skill.get("tags", []))
        typer.echo(f"  {skill['name']:<20} {skill.get('category', ''):<15} {tags}")


@app.command()
def search(query: str = typer.Argument(..., help="Search query")) -> None:
    """Search skills by name, description, or tags."""
    reg = _get_registry()
    results = reg.search(query)
    if not results:
        typer.echo("No skills found matching query.")
        return
    for skill in results:
        typer.echo(f"  {skill['name']:<20} {skill.get('description', '')}")


@app.command()
def info(name: str = typer.Argument(..., help="Skill name")) -> None:
    """Show detailed information about a skill."""
    reg = _get_registry()
    skill = reg.get(name)
    if skill is None:
        typer.echo(f"Skill '{name}' not found.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Name:         {skill['name']}")
    typer.echo(f"Description:  {skill.get('description', '')}")
    typer.echo(f"Category:     {skill.get('category', '')}")
    typer.echo(f"Tags:         {', '.join(skill.get('tags', []))}")
    typer.echo(f"Version:      {skill.get('version', '')}")
    typer.echo(f"Software:     {skill.get('software_url', '')}")
    typer.echo(f"Source:       {skill.get('source_repo', '')}")
    deps = skill.get("dependencies", [])
    if deps:
        typer.echo(f"Dependencies: {', '.join(deps)}")


@app.command()
def install(
    name: str = typer.Argument(..., help="Skill name to install"),
    project: str = typer.Option(None, "--project", "-p", help="Project directory"),
    global_: bool = typer.Option(False, "--global", "-g", help="Install globally"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing"),
) -> None:
    """Install a skill to a project or globally."""
    if not project and not global_:
        typer.echo("Specify --project <path> or --global.", err=True)
        raise typer.Exit(code=1)

    installer = _get_installer()
    try:
        dest = installer.install(
            name,
            project_path=project,
            global_install=global_,
            force=force,
        )
        typer.echo(f"Installed '{name}' to {dest}")
    except (ValueError, FileExistsError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)


@app.command()
def uninstall(
    name: str = typer.Argument(..., help="Skill name to uninstall"),
    project: str = typer.Option(None, "--project", "-p", help="Project directory"),
    global_: bool = typer.Option(False, "--global", "-g", help="Uninstall globally"),
) -> None:
    """Uninstall a skill from a project or globally."""
    if not project and not global_:
        typer.echo("Specify --project <path> or --global.", err=True)
        raise typer.Exit(code=1)

    installer = _get_installer()
    try:
        installer.uninstall(name, project_path=project, global_install=global_)
        typer.echo(f"Uninstalled '{name}'.")
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)


def main() -> None:
    app()
