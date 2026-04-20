"""Logic for `vnccs character prune` — delete a character's entire state tree.

Removes ``<state_dir>/<name>/`` recursively: character sheet, costumes,
emotions, sprites, dataset. No ComfyUI contact — pure filesystem.

Requires ``confirm=True`` (the CLI surfaces this as ``--yes``) to prevent
accidental deletion of generation work that took hours on GPU.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from vnccs_cli.backend import (
    VnccsError,
    VnccsNotFoundError,
    VnccsValidationError,
    get_vnccs_state_dir,
)


def _tree_stats(root: Path) -> dict:
    """Sum bytes + file count under ``root`` before removal."""
    total_bytes = 0
    file_count = 0
    dir_count = 0
    try:
        for item in root.rglob("*"):
            if item.is_file():
                file_count += 1
                try:
                    total_bytes += item.stat().st_size
                except OSError:
                    pass
            elif item.is_dir():
                dir_count += 1
    except OSError:
        pass
    return {
        "file_count": file_count,
        "dir_count": dir_count,
        "total_bytes": total_bytes,
    }


def run_prune(
    character: str,
    *,
    confirm: bool = False,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> dict:
    """Delete a character's state tree.

    Returns ``{character, path, removed: {file_count, dir_count, total_bytes}}``.

    Raises:
        VnccsError (exit 1): empty character argument.
        VnccsValidationError (exit 3): ``confirm=False`` — require the user
            to pass ``--yes`` explicitly.
        VnccsNotFoundError (exit 5): character directory doesn't exist.
    """
    if not character:
        raise VnccsError("character name is required")
    if not confirm:
        raise VnccsValidationError(
            "character prune requires --yes confirmation",
            detail=(
                "This permanently deletes the character sheet, every "
                "costume, every emotion, every sprite, and the LoRA "
                "dataset dir. Pass --yes if you really want this."
            ),
        )

    root = get_vnccs_state_dir(comfy_path, state_dir=state_dir).resolve()
    char_dir_raw = root / character
    # Safety: refuse paths that escape the state root via ``..`` /
    # absolute traversal, or whose resolved parent isn't ``root`` itself
    # (so character must be a direct child, not a nested path like
    # ``sub/dir``). Check BEFORE is_dir() so ``..`` can't slip through.
    char_dir = char_dir_raw.resolve()
    if char_dir.parent != root:
        raise VnccsValidationError(
            f"Refusing to prune outside the VNCCS state tree: {char_dir}",
            detail=f"Must be a direct subdir of {root}.",
        )
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {character}",
            detail=f"Expected directory {char_dir}.",
        )

    stats = _tree_stats(char_dir)
    shutil.rmtree(char_dir)
    return {
        "character": character,
        "path": str(char_dir),
        "removed": stats,
    }
