"""config command group — introspect resolved paths and URL.

Phase 3 will populate:
  @app.command("show") — print COMFY_PATH, COMFY_URL, VNCCS install dir,
                         bundled workflow directory, detected models dirs.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Show resolved VNCCS CLI configuration (paths, URLs).",
    no_args_is_help=True,
)
