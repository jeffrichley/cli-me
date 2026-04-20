"""sprite command group — stage 4 operations (final VN-ready sprites).

Phase 3 will populate:
  @app.command("render") — render sprites for every (costume x emotion)
                           combination the character has on disk. No filter
                           — per Jeff's Phase 1 scope decision.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Render final VN-ready sprites for a VNCCS character.",
    no_args_is_help=True,
)
