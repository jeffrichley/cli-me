"""convert command group — thin CLI dispatch.

Commands implemented here are filled in during Phase 3 of the build. The
sub-app itself is registered in `__init__.py`; importing this module triggers
@convert_app.command() decoration for any commands defined below.
"""

from __future__ import annotations

# from pandoc_cli import convert_app
# from pandoc_cli.commands.convert_to import build_args, run_convert
# from pandoc_cli.backend import run_pandoc, report_success
#
# Phase 3 will populate:
#   @convert_app.command("to")
#   def convert_to(input, output, from_, to, standalone, toc, ...): ...
