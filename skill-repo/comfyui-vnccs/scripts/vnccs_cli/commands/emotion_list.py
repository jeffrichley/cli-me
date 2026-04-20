"""Logic for `vnccs emotion list CHARACTER` — enumerate (costume, emotion) pairs.

Pure filesystem walk — no HTTP, no workflow submission. Enumerates every
``Sheets/<costume>/<emotion>/`` subdirectory that contains a
``sheet_<emotion>_NNNNN_.png`` file. Emotions are extended lazily by the
upstream ``EmotionGenerator`` via ``os.makedirs(face_dir, exist_ok=True)``
— so the only reliable enumeration is a directory walk.

Layout reference: ``references/source-analysis/state-management.md``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from vnccs_cli.backend import VnccsNotFoundError, get_vnccs_state_dir

# Matches sheet files for any emotion (the emotion name is captured as
# part of the directory walk, so we just need to confirm the filename
# pattern to tell a real emotion-sheet dir from a random empty one).
SHEET_PATTERN = re.compile(r"^sheet_[^/\\]+_\d+_?\.png$")


def _has_sheet_file(emotion_dir: Path) -> bool:
    """True iff ``emotion_dir`` contains at least one sheet_*_NNNNN_.png."""
    try:
        for entry in emotion_dir.iterdir():
            if entry.is_file() and SHEET_PATTERN.match(entry.name):
                return True
    except OSError:
        return False
    return False


def run_list(
    character: str,
    *,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> List[dict]:
    """Return one row per (costume, emotion) pair that has rendered sheets.

    Args:
        character: Character directory name. Must exist under the resolved
            VNCCS state directory.
        comfy_path: Optional override for COMFY_PATH.
        state_dir: Optional override for the VNCCS state directory
            (precedence: this arg > VNCCS_STATE_DIR env >
            ``<comfy>/output/VN_CharacterCreatorSuit``).

    Returns:
        List of dicts: ``{costume, emotion, path}`` where ``path`` is
        the absolute string path to the emotion subdirectory (not a
        specific sheet file — the dir may accumulate multiple runs).
        Sorted by costume then emotion. Always empty list if the
        character has no ``Sheets/`` tree yet (not an error).

    Raises:
        VnccsPathError: COMFY_PATH unresolvable (exit 6).
        VnccsNotFoundError: character directory missing (exit 5).
    """
    state_root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)
    char_dir = state_root / character
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {character!r}",
            detail=(
                f"Expected directory at {char_dir}. Create the character "
                "first with `vnccs character create NAME`."
            ),
        )

    sheets_root = char_dir / "Sheets"
    if not sheets_root.is_dir():
        return []

    rows: List[dict] = []
    try:
        costume_dirs = sorted(
            p for p in sheets_root.iterdir() if p.is_dir()
        )
    except OSError:
        return []

    for costume_dir in costume_dirs:
        try:
            emotion_dirs = sorted(
                p for p in costume_dir.iterdir() if p.is_dir()
            )
        except OSError:
            continue
        for emotion_dir in emotion_dirs:
            if not _has_sheet_file(emotion_dir):
                continue
            rows.append(
                {
                    "costume": costume_dir.name,
                    "emotion": emotion_dir.name,
                    "path": str(emotion_dir),
                }
            )
    return rows
