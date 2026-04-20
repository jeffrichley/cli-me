"""check command group — verify VNCCS + custom nodes + models + server.

Phase 3 will populate:
  @app.command("nodes") — verify every pack in REQUIRED_CUSTOM_NODE_PACKS
  @app.command("models") — cross-reference required-models.md vs disk
  @app.command("all")   — run nodes + models + server ping
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Verify VNCCS + custom nodes + models + server reachability.",
    no_args_is_help=True,
)
