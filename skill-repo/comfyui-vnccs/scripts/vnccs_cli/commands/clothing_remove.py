"""Logic for `vnccs clothing remove` — delete one costume + its emotions.

Removes ``<state_dir>/<char>/Sheets/<costume>/`` recursively and prunes
the ``costumes[<costume>]`` entry from the character's config JSON. No
ComfyUI contact — pure filesystem. Requires ``confirm=True`` (surfaced
as ``--yes``).

The special costume ``Naked`` is the base character-sheet folder (see
``utils.list_costumes``) and cannot be removed: pruning it would leave
the character with no base sheet. Attempting to remove it raises
``VnccsValidationError`` (exit 3).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

from vnccs_cli.backend import (
    VnccsError,
    VnccsNotFoundError,
    VnccsValidationError,
    get_vnccs_state_dir,
)

PROTECTED_COSTUME = "Naked"


def _tree_stats(root: Path) -> dict:
    total_bytes = 0
    file_count = 0
    try:
        for item in root.rglob("*"):
            if item.is_file():
                file_count += 1
                try:
                    total_bytes += item.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return {"file_count": file_count, "total_bytes": total_bytes}


def _strip_costume_from_config(char_dir: Path, costume: str) -> bool:
    """Remove ``costumes[<costume>]`` from the character's config JSON.

    Returns True if the config was updated, False if the config file was
    missing / unparseable / didn't mention the costume. Silent on errors
    because the on-disk dir removal is the authoritative action — a
    stale config entry is survivable; a failing rmdir is not.
    """
    config_file = char_dir / f"{char_dir.name}_config.json"
    if not config_file.is_file():
        return False
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    costumes = data.get("costumes")
    if not isinstance(costumes, dict) or costume not in costumes:
        return False
    del costumes[costume]
    try:
        config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        return False
    return True


def run_remove(
    character: str,
    costume: str,
    *,
    confirm: bool = False,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> dict:
    """Delete a costume's Sheets/ tree and strip it from the config.

    Returns ``{character, costume, path, config_updated, removed: {...}}``.

    Raises:
        VnccsError (exit 1): empty character or costume arg.
        VnccsValidationError (exit 3): ``confirm=False`` or costume is
            ``"Naked"`` (protected: it IS the base character sheet).
        VnccsNotFoundError (exit 5): character or costume directory missing.
    """
    if not character:
        raise VnccsError("character is required")
    if not costume:
        raise VnccsError("--name (costume) is required")
    if costume == PROTECTED_COSTUME:
        raise VnccsValidationError(
            f"Refusing to remove the protected base costume {PROTECTED_COSTUME!r}",
            detail=(
                "'Naked' is the base character sheet folder — deleting it "
                "would leave the character with no reference for future "
                "emotion/clothing generations. Prune the whole character "
                "with `vnccs character prune` if that's what you want."
            ),
        )
    if not confirm:
        raise VnccsValidationError(
            "clothing remove requires --yes confirmation",
            detail=(
                "This permanently deletes the costume sheet, every variant, "
                "and every emotion rendered in this costume."
            ),
        )

    root = get_vnccs_state_dir(comfy_path, state_dir=state_dir).resolve()
    char_dir = (root / character).resolve()
    if char_dir.parent != root:
        raise VnccsValidationError(
            f"Refusing to resolve character outside state tree: {char_dir}",
            detail=f"Must be a direct subdir of {root}.",
        )
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {character}",
            detail=f"Expected directory {char_dir}.",
        )
    sheets_root = (char_dir / "Sheets").resolve()
    costume_dir = (sheets_root / costume).resolve()
    if costume_dir.parent != sheets_root:
        raise VnccsValidationError(
            f"Refusing to remove outside Sheets/: {costume_dir}",
            detail=f"Must be a direct subdir of {sheets_root}.",
        )
    if not costume_dir.is_dir():
        raise VnccsNotFoundError(
            f"Costume not found: {character}/{costume}",
            detail=f"Expected directory {costume_dir}.",
        )

    stats = _tree_stats(costume_dir)
    shutil.rmtree(costume_dir)
    config_updated = _strip_costume_from_config(char_dir, costume)

    return {
        "character": character,
        "costume": costume,
        "path": str(costume_dir),
        "config_updated": config_updated,
        "removed": stats,
    }
