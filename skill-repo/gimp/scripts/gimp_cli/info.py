"""info command group."""

from __future__ import annotations

import typer

from gimp_cli import app
from gimp_cli.backend import detect_version, find_executable
from gimp_cli.commands.info import capability_flags

info_app = typer.Typer(help="Use when you need to inspect local GIMP install/version details.")
app.add_typer(info_app, name="info")


@info_app.command("version")
def version() -> None:
    """Show installed GIMP version."""
    typer.echo(detect_version())


@info_app.command("capabilities")
def capabilities() -> None:
    """Show resolved binary and core automation flags."""
    typer.echo(f"binary: {find_executable()}")
    typer.echo("flags:")
    for flag in capability_flags():
        typer.echo(f"  - {flag}")
