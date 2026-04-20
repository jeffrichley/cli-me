"""Logic for `comfyui custom-nodes remove` — delete a custom node directory."""

from __future__ import annotations

from typing import Optional

from comfyui_cli.backend import ComfyError, get_comfy_path, safe_rmtree


def run_remove(
    name: str,
    *,
    comfy_path: Optional[str] = None,
    yes: bool = False,
) -> dict:
    """Delete `<comfy_path>/custom_nodes/<name>`.

    Refuses unless `yes=True` (caller confirmed). Refuses path-traversal
    attempts (names containing `/` or `..`). Returns a dict describing
    what was removed.
    """
    if not yes:
        raise ComfyError(
            f"Refusing to remove {name!r} without explicit confirmation.",
            detail="Pass --yes to confirm. This deletes the directory recursively.",
        )
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ComfyError(
            f"Invalid custom-node name {name!r}.",
            detail="Names cannot contain path separators or be . / ..",
        )

    comfy = get_comfy_path(comfy_path)
    target = comfy / "custom_nodes" / name
    if not target.exists():
        raise ComfyError(
            f"Custom node {name!r} is not installed at {target}.",
        )
    if target.is_symlink():
        raise ComfyError(
            f"Refusing to remove symlink: {target}",
            detail=(
                "Target is a symlink — recursive delete could escape "
                "custom_nodes/. Remove the symlink manually with `rm` / "
                "`del` if you're sure."
            ),
        )
    if not target.is_dir():
        raise ComfyError(
            f"Refusing to remove non-directory: {target}",
        )

    try:
        safe_rmtree(target)
    except OSError as e:
        raise ComfyError(
            f"Could not remove {target}",
            detail=str(e),
        ) from e

    return {
        "name": name,
        "path": str(target),
        "removed": True,
        "restart_required": True,
    }
