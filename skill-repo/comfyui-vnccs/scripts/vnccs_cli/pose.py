"""pose command group — enumerate bundled pose presets.

Phase 3 will populate:
  @app.command("list") — list preset images from VNCCS/presets/poses/
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="List pose presets from the installed VNCCS node pack's presets/poses/ directory.",
    no_args_is_help=True,
)
