"""Logic for `comfyui custom-nodes list` — enumerate installed custom node packs."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from comfyui_cli.backend import ComfyPathError, get_comfy_path

# Subdirectories of custom_nodes/ that are not real custom nodes — skip them.
# Note: only directory names belong here; `.py` / `.py.example` files are
# already filtered by the `is_dir()` check below.
_IGNORE_NAMES = {
    "__pycache__",
    ".DS_Store",
}


def _git_describe(node_dir: Path) -> dict:
    """Best-effort git introspection. Returns {} if not a git repo or git missing."""
    if not (node_dir / ".git").exists():
        return {}
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(node_dir),
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(node_dir),
            capture_output=True,
            text=True,
            timeout=5,
        )
        remote = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(node_dir),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    info: dict = {}
    if commit.returncode == 0:
        info["commit"] = commit.stdout.strip()
    if branch.returncode == 0:
        info["branch"] = branch.stdout.strip()
    if remote.returncode == 0:
        info["remote"] = remote.stdout.strip()
    return info


def run_list(*, comfy_path: Optional[str] = None) -> list[dict]:
    """Return a list of installed custom node packs.

    Each entry: {"name", "path", "is_git", "has_requirements", "commit"?,
    "branch"?, "remote"?}.
    """
    comfy = get_comfy_path(comfy_path)
    custom_nodes = comfy / "custom_nodes"

    try:
        entries = sorted(custom_nodes.iterdir())
    except OSError as e:
        raise ComfyPathError(
            f"Could not read custom_nodes directory: {custom_nodes}",
            detail=str(e),
        ) from e

    nodes: list[dict] = []
    for entry in entries:
        if entry.name in _IGNORE_NAMES:
            continue
        if not entry.is_dir():
            continue
        info: dict = {
            "name": entry.name,
            "path": str(entry),
            "is_git": (entry / ".git").exists(),
            "has_requirements": (entry / "requirements.txt").exists(),
        }
        info.update(_git_describe(entry))
        nodes.append(info)
    return nodes
