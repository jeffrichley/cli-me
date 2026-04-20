"""character command group — stage 1 + 1.1 operations.

Phase 3 will populate:
  @app.command("create") — generate character sheet from prompt (stage 1)
  @app.command("clone")  — derive from existing character (stage 1.1)
  @app.command("list")   — enumerate saved characters
  @app.command("show")   — inspect details + generated artifacts
  @app.command("prune")  — delete a character and all derived data
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Create / clone / list / inspect / prune VNCCS characters.",
    no_args_is_help=True,
)
