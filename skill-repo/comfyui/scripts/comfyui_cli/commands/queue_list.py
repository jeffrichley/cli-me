"""queue list — alias for `queue status` (no id).

Kept as a separate command for discoverability per the wiki. Delegates to
`queue_status.run_status(prompt_id=None, ...)`.
"""

from __future__ import annotations

from typing import Optional

from comfyui_cli.commands import queue_status


def run_list(
    *,
    url: Optional[str] = None,
    json_output: bool = False,
) -> None:
    """GET /queue and render queue_running + queue_pending as a Rich table."""
    queue_status.run_status(
        prompt_id=None, url=url, json_output=json_output
    )
