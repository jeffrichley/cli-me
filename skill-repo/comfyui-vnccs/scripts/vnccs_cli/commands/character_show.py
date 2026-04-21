"""Logic for `vnccs character show NAME` — inspect a character's artifact tree.

Pure filesystem. Raises `VnccsNotFoundError` (exit 5) if the character
directory does not exist; raises `VnccsPathError` (exit 6) if the state
dir is unresolvable (e.g. COMFY_PATH unset).

State layout reference: references/source-analysis/state-management.md.

Artifacts surfaced:

  - The per-character config at `{name}/{name}_config.json` (if present).
  - Character sheet: highest-numbered `sheet_neutral_NNNNN_.png` under
    `Sheets/Naked/neutral/` per `utils.load_character_sheet`'s
    directory walk. We surface presence + path + size.
  - Costumes: every subdirectory of `Sheets/`. Variant count is the
    number of `*.png` files in `Sheets/{costume}/neutral/` (VNCCS's
    `Step 2` stages N variants and `clothing pick` will later pick
    one). `picked_variant` reads the `costumes.{name}.picked_variant`
    key from config.json when present, else None.
  - Emotions: every `(costume, emotion)` subdirectory except the
    `neutral` base, flattened. Each entry has the path of the highest-
    numbered sheet file.
  - Sprites: count of `*.png` files under `Sprites/` (recursive), which
    is what Stage 4 (`sprite render`) materializes.
  - Dataset: existence of `lora/` and the number of caption-text rows
    in it (one per `.txt` companion of a PNG).

The function returns a plain dict; the dispatch layer decides whether
to render a Rich view or emit JSON.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from vnccs_cli.backend import (
    VnccsNotFoundError,
    get_vnccs_state_dir,
)

# Matches `sheet_{emotion}_NNNNN_.png`, `face_{emotion}_NNNNN_.png`,
# `sprite_{emotion}_NNNNN_.png`. `NNNNN` is the ComfyUI-assigned integer.
# Mirror of `utils.load_character_sheet`'s intent: pick the highest N.
_NUM_RE = re.compile(r"_(\d+)_")


def _highest_numbered_png(directory: Path) -> Optional[Path]:
    """Return the PNG with the highest embedded number, or None."""
    if not directory.is_dir():
        return None
    best: tuple[int, Path] | None = None
    try:
        for entry in directory.iterdir():
            if not entry.is_file() or entry.suffix.lower() != ".png":
                continue
            match = _NUM_RE.search(entry.name)
            if match is None:
                continue
            num = int(match.group(1))
            if best is None or num > best[0]:
                best = (num, entry)
    except OSError:
        return None
    return best[1] if best else None


def _load_config(config_path: Path) -> Optional[dict[str, Any]]:
    """Parse `{name}_config.json`. Returns None on any read/parse error."""
    if not config_path.is_file():
        return None
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _list_costumes(char_dir: Path, config: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enumerate costumes.

    Walks `Sheets/` for the source of truth (matches
    `utils.list_costumes`'s fallback behaviour of listing Sheets/ dirs
    even if they aren't declared in config). For each costume, reports
    variant count (number of `.png` files in `Sheets/{costume}/neutral/`)
    and the `picked_variant` key from config when present.
    """
    sheets_root = char_dir / "Sheets"
    costumes: list[dict[str, Any]] = []
    if not sheets_root.is_dir():
        return costumes

    config_costumes = {}
    if config and isinstance(config.get("costumes"), dict):
        config_costumes = config["costumes"]

    try:
        entries = [e for e in sheets_root.iterdir() if e.is_dir()]
    except OSError:
        return costumes

    # VNCCS contract (utils.py:list_costumes): Naked first, then the rest
    # alphabetically. Matches state-management.md:237-240.
    entries.sort(key=lambda p: (0 if p.name == "Naked" else 1, p.name))

    for entry in entries:
        neutral_dir = entry / "neutral"
        variant_count = 0
        if neutral_dir.is_dir():
            try:
                variant_count = sum(
                    1
                    for f in neutral_dir.iterdir()
                    if f.is_file() and f.suffix.lower() == ".png"
                )
            except OSError:
                variant_count = 0

        picked = None
        costume_cfg = config_costumes.get(entry.name)
        if isinstance(costume_cfg, dict):
            raw = costume_cfg.get("picked_variant")
            if isinstance(raw, (str, int)):
                picked = raw

        costumes.append(
            {
                "name": entry.name,
                "variant_count": variant_count,
                "picked_variant": picked,
            }
        )
    return costumes


def _list_emotions(char_dir: Path) -> list[dict[str, Any]]:
    """Enumerate every non-`neutral` emotion sheet across all costumes.

    Returns one row per (costume, emotion) directory containing at least
    one sheet PNG. "emotion_type" is the bare directory name
    (`shy-blush`, `angry`, etc. per `emotions-config/emotions.json`).
    """
    sheets_root = char_dir / "Sheets"
    emotions: list[dict[str, Any]] = []
    if not sheets_root.is_dir():
        return emotions

    try:
        costumes = sorted(
            [c for c in sheets_root.iterdir() if c.is_dir()],
            key=lambda p: p.name,
        )
    except OSError:
        return emotions

    for costume_dir in costumes:
        try:
            emotion_dirs = sorted(
                [e for e in costume_dir.iterdir() if e.is_dir()],
                key=lambda p: p.name,
            )
        except OSError:
            continue
        for emotion_dir in emotion_dirs:
            if emotion_dir.name == "neutral":
                # The base sheet lives at Naked/neutral; don't report
                # it as an emotion record (matches VNCCS semantics).
                continue
            sheet = _highest_numbered_png(emotion_dir)
            if sheet is None:
                continue
            emotions.append(
                {
                    "costume": costume_dir.name,
                    "emotion_type": emotion_dir.name,
                    "path": str(sheet),
                }
            )
    return emotions


def _count_pngs_recursive(directory: Path) -> int:
    """Count .png files under `directory` (recursive).

    Skips the known-broken VNCCS emotion aggregates
    (``sprite_<emotion>__00001_.png`` and
    ``sheet_<emotion>__00001.png`` for non-neutral emotions — the
    silhouette misfires from Step3's SaveImageWithAlpha bug). See
    ``backend.is_broken_emotion_aggregate`` and gotchas.md.
    """
    from vnccs_cli.backend import is_broken_emotion_aggregate

    if not directory.is_dir():
        return 0
    count = 0
    try:
        for f in directory.rglob("*.png"):
            if not f.is_file():
                continue
            if is_broken_emotion_aggregate(f):
                continue
            count += 1
    except OSError:
        return 0
    return count


def _dataset_stats(char_dir: Path) -> dict[str, Any]:
    """Inspect `lora/` subdir: exists + row count (one `.txt` per row)."""
    lora_dir = char_dir / "lora"
    if not lora_dir.is_dir():
        return {"exists": False, "path": str(lora_dir), "row_count": 0}
    row_count = 0
    try:
        for f in lora_dir.iterdir():
            if f.is_file() and f.suffix.lower() == ".txt":
                row_count += 1
    except OSError:
        pass
    return {"exists": True, "path": str(lora_dir), "row_count": row_count}


def _character_sheet(char_dir: Path) -> dict[str, Any]:
    """Find the base character sheet (`Sheets/Naked/neutral/sheet_*.png`)."""
    base_dir = char_dir / "Sheets" / "Naked" / "neutral"
    sheet = _highest_numbered_png(base_dir)
    if sheet is None:
        return {"present": False, "path": None, "size": 0}
    try:
        size = sheet.stat().st_size
    except OSError:
        size = 0
    return {"present": True, "path": str(sheet), "size": size}


def run_show(
    name: str,
    *,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> dict[str, Any]:
    """Return a structured inspection record for one character.

    Raises VnccsNotFoundError (exit 5) if NAME has no directory under
    the VNCCS state root.
    """
    root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)
    char_dir = root / name
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {name}",
            detail=(
                f"Expected directory at {char_dir}. "
                f"Run `vnccs character list` to see existing characters."
            ),
        )

    config_path = char_dir / f"{name}_config.json"
    config = _load_config(config_path)
    sprites_dir = char_dir / "Sprites"

    return {
        "name": name,
        "state_path": str(char_dir),
        "config": {
            "path": str(config_path),
            "present": config is not None,
        },
        "character_sheet": _character_sheet(char_dir),
        "costumes": _list_costumes(char_dir, config),
        "emotions": _list_emotions(char_dir),
        "sprites": {
            "path": str(sprites_dir),
            "exists": sprites_dir.is_dir(),
            "png_count": _count_pngs_recursive(sprites_dir),
        },
        "dataset": _dataset_stats(char_dir),
    }
