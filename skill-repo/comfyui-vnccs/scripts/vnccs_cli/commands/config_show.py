"""Logic for `vnccs config show` — report resolved paths + URL.

Pure filesystem + env inspection — no HTTP calls to ComfyUI. Mirrors the
`comfyui info` pattern: return a plain dict for the dispatch layer to
render as either a Rich table or raw JSON.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from vnccs_cli.backend import (
    DEFAULT_COMFY_URL,
    VNCCS_CUSTOM_NODE_DIR_NAME,
    VnccsPathError,
    get_comfy_path,
)


def _parse_vnccs_version(vnccs_dir: Path) -> str:
    """Read the VNCCS node pack's pyproject.toml for a version string.

    Falls back to "unknown" if pyproject.toml is missing, unreadable, or
    has no parseable version line. Does NOT use tomllib so the parse is
    resilient to partially-written or non-standard TOML the user may have
    edited.
    """
    pyproject = vnccs_dir / "pyproject.toml"
    if not pyproject.is_file():
        return "unknown"
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    # Match a top-level `version = "x.y.z"` line (common in [project] block).
    match = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match:
        return match.group(1)
    return "unknown"


def _bundled_workflow_dir() -> Path:
    """Absolute path to this skill's scripts/workflows/ directory.

    Mirrors `backend.bundled_workflow_path` but returns the directory
    itself (not an individual file). Resolved relative to this file so it
    works regardless of cwd.
    """
    return (Path(__file__).resolve().parent.parent.parent / "workflows").resolve()


def run_show(*, comfy_path: Optional[str] = None, url: Optional[str] = None) -> dict:
    """Resolve VNCCS CLI config and return it as a dict.

    Keys (always present, strings):
      - comfy_path          resolved ComfyUI install dir
      - comfy_url           resolved base URL (no trailing slash)
      - vnccs_install_dir   <comfy_path>/custom_nodes/ComfyUI_VNCCS
      - vnccs_version       parsed from pyproject.toml or "unknown"
      - bundled_workflow_dir absolute path to scripts/workflows/
      - models_root         <comfy_path>/models
      - output_dir          <comfy_path>/output

    Raises:
        VnccsPathError: COMFY_PATH unresolvable (exit 6). The VNCCS install
            dir key is filled in even when VNCCS itself isn't installed —
            we just report the expected path so the user can see where to
            put it.
    """
    comfy = get_comfy_path(comfy_path)
    vnccs_dir = comfy / "custom_nodes" / VNCCS_CUSTOM_NODE_DIR_NAME

    resolved_url = url or os.environ.get("COMFY_URL") or DEFAULT_COMFY_URL
    resolved_url = resolved_url.rstrip("/")

    return {
        "comfy_path": str(comfy),
        "comfy_url": resolved_url,
        "vnccs_install_dir": str(vnccs_dir),
        "vnccs_version": _parse_vnccs_version(vnccs_dir),
        "bundled_workflow_dir": str(_bundled_workflow_dir()),
        "models_root": str(comfy / "models"),
        "output_dir": str(comfy / "output"),
    }
