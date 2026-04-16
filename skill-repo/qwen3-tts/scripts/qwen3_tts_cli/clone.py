"""Clone command group — voice cloning from reference audio."""

import typer

from . import app

clone_app = typer.Typer(help="Voice cloning from reference audio.", no_args_is_help=True)
app.add_typer(clone_app, name="clone")
