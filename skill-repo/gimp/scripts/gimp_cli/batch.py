"""batch command group."""

from __future__ import annotations

import typer

from gimp_cli import app
from gimp_cli.backend import detect_version, run_command
from gimp_cli.commands.batch import build_batch_args

batch_app = typer.Typer(help="Use when you need repeatable headless Script-Fu/Python batch runs.")
app.add_typer(batch_app, name="batch")


def _supports_quit_flag(version_text: str) -> bool:
    """Return True when installed GIMP supports --quit."""
    # GIMP 2.10 on Windows does not accept --quit, while newer lines do.
    return "version 2." not in version_text.lower()


@batch_app.command("run")
def run(
    command: list[str] = typer.Option(
        ...,
        "--command",
        "-c",
        help="Batch expression. Repeat for multiple expressions.",
    ),
    interpreter: str = typer.Option(
        None,
        "--interpreter",
        help="Optional batch interpreter procedure (for example: python-fu-eval).",
    ),
    no_data: bool = typer.Option(
        False,
        "--no-data",
        help="Skip loading brushes/gradients/patterns for faster startup.",
    ),
    no_fonts: bool = typer.Option(
        False,
        "--no-fonts",
        help="Skip loading fonts for faster startup.",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose GIMP logs."),
    keep_alive: bool = typer.Option(
        False,
        "--keep-alive",
        help="Do not append --quit at the end of the batch run.",
    ),
) -> None:
    """Run one or more batch expressions with safe headless defaults."""
    version_text = detect_version()
    args = build_batch_args(
        command,
        interpreter=interpreter,
        no_data=no_data,
        no_fonts=no_fonts,
        verbose=verbose,
        quit_after=not keep_alive,
        quit_via_flag=_supports_quit_flag(version_text),
    )
    result = run_command(args, check=False)
    if result.stdout:
        typer.echo(result.stdout, nl=False)
    if result.stderr:
        typer.echo(result.stderr, err=True, nl=False)
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)
