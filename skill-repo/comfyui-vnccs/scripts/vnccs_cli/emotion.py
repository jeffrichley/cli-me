"""emotion command group — stage 3 operations (emotion sheets per character/costume).

Phase 3 will populate:
  @app.command("add") — generate emotion sheet (defaults to --legacy SDXL;
                        --qwen opts into broken upstream QWEN path)
  @app.command("list")
  @app.command("show")
  @app.command("preview") — show a pre-rendered emotion sample

Upstream bug note (see references/gotchas.md): VNCCS 2.1.0's QWEN emotion
workflow references VNCCS_QWEN_Detailer and VNCCS_BBox_Extractor which are
not registered in any published branch. `--legacy` uses the working SDXL
workflow (V1SDXL/) and is the default until upstream ships the missing
Python classes.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Add / list / show / preview emotion sheets for VNCCS characters.",
    no_args_is_help=True,
)
