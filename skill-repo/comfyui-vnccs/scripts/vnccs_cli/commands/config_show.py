"""Logic for `vnccs config show` — report resolved paths + URL.

Pure filesystem + env inspection — no HTTP calls to ComfyUI. Mirrors the
`comfyui info` pattern: return a plain dict for the dispatch layer to
render as either a Rich table or raw JSON.
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Optional

from vnccs_cli.backend import (
    DEFAULT_COMFY_URL,
    VNCCS_CUSTOM_NODE_DIR_NAME,
    get_comfy_path,
    get_vnccs_state_dir,
)


def _parse_vnccs_version(vnccs_dir: Path) -> str:
    """Read ``[project].version`` from the VNCCS node pack's pyproject.toml.

    Uses ``tomllib`` so we correctly scope to the ``[project]`` table
    (not a ``[tool.poetry.dependencies.*]`` block that happens to have a
    ``version`` line before ``[project]``). Falls back to a lenient regex
    and finally to ``"unknown"`` when both fail — matches the intent of
    the docstring contract: never raise, always return a string.
    """
    pyproject = vnccs_dir / "pyproject.toml"
    if not pyproject.is_file():
        return "unknown"
    try:
        raw = pyproject.read_bytes()
    except OSError:
        return "unknown"
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        # Malformed TOML — fall back to the lenient regex below.
        data = None
    if isinstance(data, dict):
        project = data.get("project")
        if isinstance(project, dict):
            version = project.get("version")
            if isinstance(version, str) and version:
                return version
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        return "unknown"
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
      - vnccs_state_dir     resolved via get_vnccs_state_dir (honors
                            VNCCS_STATE_DIR env); this is what every
                            command actually reads, so it's what we
                            report rather than a hard-coded
                            <comfy_path>/output that other commands
                            would disagree with.

    Raises:
        VnccsPathError: COMFY_PATH unresolvable (exit 6). The VNCCS install
            dir key is filled in even when VNCCS itself isn't installed —
            we just report the expected path so the user can see where to
            put it.
    """
    comfy = get_comfy_path(comfy_path)
    vnccs_dir = comfy / "custom_nodes" / VNCCS_CUSTOM_NODE_DIR_NAME
    state_dir = get_vnccs_state_dir(comfy_path)

    resolved_url = url or os.environ.get("COMFY_URL") or DEFAULT_COMFY_URL
    resolved_url = resolved_url.rstrip("/")

    return {
        "comfy_path": str(comfy),
        "comfy_url": resolved_url,
        "vnccs_install_dir": str(vnccs_dir),
        "vnccs_version": _parse_vnccs_version(vnccs_dir),
        "bundled_workflow_dir": str(_bundled_workflow_dir()),
        "models_root": str(comfy / "models"),
        "vnccs_state_dir": str(state_dir),
    }
