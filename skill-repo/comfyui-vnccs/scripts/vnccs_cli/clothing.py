"""clothing command group — stage 2 operations (costume sets per character).

Phase 3 will populate:
  @app.command("add")    — generate N clothing variants for a character
  @app.command("list")   — enumerate costumes (optionally per character)
  @app.command("remove") — delete a costume set
  @app.command("pick")   — pick one variant from a multi-variant costume
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Add / list / remove / pick clothing variants per VNCCS character.",
    no_args_is_help=True,
)
