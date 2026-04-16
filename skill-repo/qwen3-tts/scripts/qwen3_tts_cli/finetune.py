"""Finetune command group — custom voice model training pipeline."""

import typer

from . import app

finetune_app = typer.Typer(help="Fine-tune custom voice models.", no_args_is_help=True)
app.add_typer(finetune_app, name="finetune")
