"""GIMP CLI package."""

import typer

app = typer.Typer(
    name="gimp-cli",
    help="Agent-native CLI for GIMP batch automation.",
    no_args_is_help=True,
)

from gimp_cli import batch  # noqa: E402,F401
from gimp_cli import info  # noqa: E402,F401
from gimp_cli import pod  # noqa: E402,F401
