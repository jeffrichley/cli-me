"""Design command group — voice design from natural language descriptions."""

import typer

from . import app

design_app = typer.Typer(help="Voice design from natural language descriptions.", no_args_is_help=True)
app.add_typer(design_app, name="design")
