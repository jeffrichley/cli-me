"""templates command group — thin CLI dispatch.

Phase 3 fills in:
  @templates_app.command("print") — pandoc --print-default-template=FORMAT
  @templates_app.command("apply") — convert with --template
  @templates_app.command("eisvogel") — convert to PDF using bundled Eisvogel
"""

from __future__ import annotations
