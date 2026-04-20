"""dataset command group — stage 5 operations (LoRA training dataset export).

Phase 3 will populate:
  @app.command("export")  — package sprites + captions into a kohya-style
                            dataset directory
  @app.command("preview") — dry-run; show what export WOULD produce
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Export VNCCS-generated sprites as LoRA training datasets.",
    no_args_is_help=True,
)
