"""Logic for `vnccs character list` — enumerate saved VNCCS characters.

Pure filesystem — does NOT call the ComfyUI HTTP API. Re-implements a
thin version of `ComfyUI_VNCCS/utils.py:list_characters()` so we do not
take a runtime dependency on the custom-node package (it is not in our
deps and only importable inside ComfyUI's own Python env).

State layout reference: references/source-analysis/state-management.md.
Per character, the tree is:

    <state_dir>/
      {name}/
        {name}_config.json
        Sheets/
          Naked/neutral/ ...
          {costume}/{emotion}/ ...
        Faces/ ...
        Sprites/ ...
        lora/ ...

`list_characters()` is a sorted `os.listdir()` of `base_output_dir()`.
We replicate the same contract: sorted subdirectory names; silently
return [] when the state dir does not exist yet.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from vnccs_cli.backend import get_vnccs_state_dir


def _count_costumes_and_emotions(char_dir: Path) -> tuple[int, int]:
    """Count costumes and total emotion directories under a character.

    A "costume" is any subdirectory of `Sheets/` (VNCCS creates them
    there via `ensure_costume_structure`). Emotions are subdirectories
    under each costume directory. The count is summed across costumes.

    Tolerant: missing `Sheets/` = zero costumes / zero emotions.
    """
    sheets_dir = char_dir / "Sheets"
    if not sheets_dir.is_dir():
        return 0, 0

    costume_count = 0
    emotion_count = 0
    try:
        for entry in sheets_dir.iterdir():
            if not entry.is_dir():
                continue
            costume_count += 1
            try:
                emotion_count += sum(1 for e in entry.iterdir() if e.is_dir())
            except OSError:
                # Unreadable costume subdir — treat as zero emotions.
                pass
    except OSError:
        return 0, 0
    return costume_count, emotion_count


def _character_last_modified(char_dir: Path) -> Optional[float]:
    """Return mtime (unix seconds) of the character directory, or None."""
    try:
        return char_dir.stat().st_mtime
    except OSError:
        return None


def _fmt_mtime(ts: Optional[float]) -> str:
    """ISO-8601 in UTC; empty string when unknown."""
    if ts is None:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def run_list(
    *,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Return a list of character records under the VNCCS state directory.

    Each record: {"name", "path", "costume_count", "emotion_count",
    "last_modified" (ISO-8601 UTC or ""), "last_modified_epoch" (float or None)}.

    Empty list if the state directory does not exist yet (VNCCS creates
    it lazily the first time any character is generated).
    """
    root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)
    if not root.is_dir():
        return []

    records: list[dict[str, Any]] = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name)
    except OSError:
        return []

    for entry in entries:
        if not entry.is_dir():
            continue
        costumes, emotions = _count_costumes_and_emotions(entry)
        mtime = _character_last_modified(entry)
        records.append(
            {
                "name": entry.name,
                "path": str(entry),
                "costume_count": costumes,
                "emotion_count": emotions,
                "last_modified": _fmt_mtime(mtime),
                "last_modified_epoch": mtime,
            }
        )
    return records
