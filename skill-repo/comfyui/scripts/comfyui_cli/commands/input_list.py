"""input list — requires --local (ComfyUI exposes no listing endpoint).

ComfyUI has no HTTP route to list the input/ directory. The `--local` flag
enables filesystem listing under `<COMFY_ROOT>/input/` (default
`E:\\workspaces\\tools\\comfy\\ComfyUI`). This only works when the CLI and
server share a filesystem.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from comfyui_cli.backend import ComfyError, ComfyNotFoundError, ComfyValidationError


_console = Console()

DEFAULT_COMFY_ROOT = r"E:\workspaces\tools\comfy\ComfyUI"


def _resolve_comfy_root() -> Path:
    """Resolve the ComfyUI install root from COMFY_ROOT env or the default."""
    raw = os.environ.get("COMFY_ROOT") or DEFAULT_COMFY_ROOT
    return Path(raw)


def _validate_subfolder(subfolder: Optional[str]) -> None:
    """Client-side check: reject `..` traversal. Parallel to input_upload."""
    if subfolder is None or subfolder == "":
        return
    parts = subfolder.replace("\\", "/").split("/")
    if any(p == ".." for p in parts):
        raise ComfyValidationError(
            f"Subfolder may not contain '..': {subfolder!r}. "
            "Relative-escape paths are rejected client-side."
        )


def run_list(
    *,
    subfolder: Optional[str] = None,
    local: bool = False,
    url: Optional[str] = None,
    json_output: bool = False,
) -> None:
    """List input images. Requires `--local` (no server-side listing endpoint).

    Raises:
        ComfyError (exit 3): --local not passed.
        ComfyNotFoundError (exit 5): input dir does not exist on this host.
    """
    # `url` is accepted for CLI symmetry but unused; the server has no listing.
    del url

    if not local:
        raise ComfyValidationError(
            "ComfyUI does not expose an /input listing endpoint. "
            "Use --local to list files from `<ComfyUI>/input/` on the server "
            "host (requires CLI and server to share filesystem).",
        )

    _validate_subfolder(subfolder)

    root = _resolve_comfy_root()
    input_dir = root / "input"
    if subfolder:
        input_dir = input_dir / subfolder

    if not input_dir.is_dir():
        raise ComfyNotFoundError(
            f"Input directory not found: {input_dir}. "
            "Set COMFY_ROOT env var to your ComfyUI install path.",
        )

    entries: list[dict] = []
    for path in sorted(input_dir.iterdir()):
        if path.is_file():
            entries.append(
                {
                    "name": path.name,
                    "size": path.stat().st_size,
                    "subfolder": subfolder or "",
                }
            )

    if json_output:
        sys.stdout.write(json.dumps(entries, indent=2))
        sys.stdout.write("\n")
        sys.stdout.flush()
        return

    if not entries:
        _console.print(f"[dim](no files in {input_dir})[/dim]")
        return

    table = Table(
        title=f"Input files: {input_dir}", title_style="bold"
    )
    table.add_column("Name")
    table.add_column("Size", justify="right")
    for item in entries:
        table.add_row(item["name"], f"{item['size']:,}")
    _console.print(table)
