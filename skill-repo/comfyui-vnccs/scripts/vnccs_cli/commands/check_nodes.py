"""Logic for `vnccs check nodes` — verify required custom-node packs on disk.

Per playbook.md §check nodes:
- For every pack in `backend.REQUIRED_CUSTOM_NODE_PACKS`, verify
  `<COMFY_PATH>/custom_nodes/<pack>/` exists AND contains at least one
  `.py` file. An empty directory is treated as missing.
- Returns a structured list of dicts (name / present / path / reason) so the
  Typer command layer can render a Rich table and pick an exit code.
- Raises `VnccsPathError` (exit 6) if COMFY_PATH is missing or not a real
  ComfyUI install — matches the fail-fast behavior used by sibling
  commands in this skill.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from vnccs_cli.backend import REQUIRED_CUSTOM_NODE_PACKS, get_comfy_path


def _pack_has_python_files(pack_dir: Path) -> bool:
    """True if `pack_dir` contains at least one `.py` file.

    Walks the directory tree so that packs with `__init__.py` under a
    subpackage (e.g. `ComfyUI-Impact-Pack/impact/__init__.py`) still
    count as "present". An empty or pyfile-less directory counts as
    missing per playbook.
    """
    try:
        return any(pack_dir.rglob("*.py"))
    except OSError:
        return False


def run_check_nodes(*, comfy_path: Optional[str] = None) -> list[dict]:
    """Check every required custom-node pack and return a structured report.

    Each entry: {"name": str, "path": str, "present": bool, "reason": str}.
    `reason` is "" when present, otherwise a short explanation
    ("directory missing" / "no .py files").

    Raises:
        VnccsPathError: COMFY_PATH unset / not a ComfyUI install (exit 6).
    """
    comfy = get_comfy_path(comfy_path)
    custom_nodes = comfy / "custom_nodes"

    results: list[dict] = []
    for pack in REQUIRED_CUSTOM_NODE_PACKS:
        pack_dir = custom_nodes / pack
        if not pack_dir.is_dir():
            results.append(
                {
                    "name": pack,
                    "path": str(pack_dir),
                    "present": False,
                    "reason": "directory missing",
                }
            )
            continue
        if not _pack_has_python_files(pack_dir):
            results.append(
                {
                    "name": pack,
                    "path": str(pack_dir),
                    "present": False,
                    "reason": "no .py files",
                }
            )
            continue
        results.append(
            {
                "name": pack,
                "path": str(pack_dir),
                "present": True,
                "reason": "",
            }
        )
    return results
