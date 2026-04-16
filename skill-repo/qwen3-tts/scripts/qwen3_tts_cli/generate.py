"""Generate command group — text-to-speech with built-in speakers."""

import typer

from . import app

generate_app = typer.Typer(help="Text-to-speech generation with built-in speakers.", no_args_is_help=True)
app.add_typer(generate_app, name="generate")
