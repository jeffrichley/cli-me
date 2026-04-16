"""Info command group — inspect speakers, languages, and device info."""

import typer

from . import app

info_app = typer.Typer(help="Inspect speakers, languages, and device info.", no_args_is_help=True)
app.add_typer(info_app, name="info")
