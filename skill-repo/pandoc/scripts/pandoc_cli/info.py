"""info command group — thin CLI dispatch.

Each command is a Typer-decorated wrapper around a `run_*` function in
``pandoc_cli.commands.info_*`` that contains the testable logic. This split
keeps Typer plumbing (argument parsing, exit codes, formatting) separate from
business logic so Tier 1 tests can call ``run_*`` directly.
"""

from __future__ import annotations

import typer

from pandoc_cli import info_app
from pandoc_cli.commands.info_engines import run_engines
from pandoc_cli.commands.info_formats import run_formats
from pandoc_cli.commands.info_version import run_version


@info_app.command("version")
def cmd_version() -> None:
    """Show installed pandoc version."""
    typer.echo(run_version())


@info_app.command("formats")
def cmd_formats(
    input_only: bool = typer.Option(
        False,
        "--input",
        help="List input formats only.",
    ),
    output_only: bool = typer.Option(
        False,
        "--output",
        help="List output formats only.",
    ),
) -> None:
    """List pandoc input and/or output formats.

    Without flags, both columns ("INPUT" and "OUTPUT") are printed.
    ``--input`` and ``--output`` are mutually exclusive.
    """
    if input_only and output_only:
        typer.echo(
            "ERROR: --input and --output are mutually exclusive. "
            "Pass neither to list both.",
            err=True,
        )
        raise typer.Exit(code=1)

    if input_only:
        side = "input"
    elif output_only:
        side = "output"
    else:
        side = "both"

    result = run_formats(side=side)

    if side in ("both", "input"):
        typer.echo("INPUT")
        for fmt in result["input"]:
            typer.echo(f"  {fmt}")
        if side == "both":
            typer.echo("")
    if side in ("both", "output"):
        typer.echo("OUTPUT")
        for fmt in result["output"]:
            typer.echo(f"  {fmt}")


@info_app.command("engines")
def cmd_engines() -> None:
    """List PDF engines on PATH (Available vs. Not installed)."""
    result = run_engines()

    typer.echo("Available")
    for engine in result["available"]:
        typer.echo(f"  {engine}")

    typer.echo("")
    typer.echo("Not installed")
    for engine in result["missing"]:
        typer.echo(f"  {engine}  (not installed)")
