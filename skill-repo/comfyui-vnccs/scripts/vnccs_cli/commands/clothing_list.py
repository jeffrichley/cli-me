"""Logic for `vnccs clothing list [CHARACTER]` — enumerate costumes.

Pure filesystem walk — no HTTP, no workflow submission. Mirrors the
upstream ``utils.list_costumes`` convention (always include ``Naked``
first), but extends it with variant counts + picked-variant introspection
so the wrapper can power a Rich table or JSON payload.

Layout reference: ``references/source-analysis/state-management.md``.
Costumes live under ``<comfy>/output/VN_CharacterCreatorSuit/<character>/
Sheets/<costume>/neutral/sheet_neutral_NNNNN_.png``. The per-character
``<character>_config.json`` carries a ``costumes`` dict; each entry MAY
contain a ``picked_variant`` int matching the ``NNNNN`` sequence of the
user's selected variant (written by ``vnccs clothing pick`` in Wave 2).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

from vnccs_cli.backend import VnccsNotFoundError, get_vnccs_state_dir

SHEET_NEUTRAL_PATTERN = re.compile(r"sheet_neutral_(\d+)_?\.png$")


def _load_config(char_dir: Path) -> dict:
    """Read ``<character>/<character>_config.json`` or return ``{}``.

    Missing config is not an error — a character directory may exist
    without a config (e.g. manually-created slot). Callers treat the
    returned dict as authoritative for ``costumes`` metadata only.
    """
    config_file = char_dir / f"{char_dir.name}_config.json"
    if not config_file.is_file():
        return {}
    try:
        return json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _costume_names(char_dir: Path) -> List[str]:
    """Enumerate costume names for a character.

    Mirrors ``utils.list_costumes``: always includes ``Naked`` first, then
    costumes declared in the config, then any costume subdir found under
    ``Sheets/`` that isn't already listed (tolerates manually-added
    costume directories).
    """
    names: List[str] = ["Naked"]

    config = _load_config(char_dir)
    for name in config.get("costumes", {}).keys():
        if name not in names:
            names.append(name)

    sheets_dir = char_dir / "Sheets"
    if sheets_dir.is_dir():
        try:
            for entry in sheets_dir.iterdir():
                if entry.is_dir() and entry.name not in names:
                    names.append(entry.name)
        except OSError:
            pass
    return names


def _count_variants(char_dir: Path, costume: str) -> int:
    """Count ``sheet_neutral_*.png`` files under ``Sheets/<costume>/neutral/``.

    Each file is one accumulated variant from a past ``clothing add`` run.
    Returns 0 if the directory is missing (newly-declared costume, no
    generation yet).
    """
    neutral = char_dir / "Sheets" / costume / "neutral"
    if not neutral.is_dir():
        return 0
    count = 0
    try:
        for entry in neutral.iterdir():
            if entry.is_file() and SHEET_NEUTRAL_PATTERN.search(entry.name):
                count += 1
    except OSError:
        return 0
    return count


def _picked_variant(config: dict, costume: str) -> Optional[int]:
    """Return the picked variant sequence number, or None if unset.

    Reads ``config["costumes"][<costume>]["picked_variant"]``. Returns
    None if the costume isn't in the config, has no ``picked_variant``
    key, or stores a non-integer value (defensive: don't crash on stale
    schemas).
    """
    costume_entry = config.get("costumes", {}).get(costume)
    if not isinstance(costume_entry, dict):
        return None
    picked = costume_entry.get("picked_variant")
    if isinstance(picked, int):
        return picked
    return None


def _costume_rows_for_character(char_dir: Path, character: str) -> List[dict]:
    """Per-costume rows for a single character. Used by both modes.

    Each row: ``{character, costume, variant_count, picked_variant}``.
    ``picked_variant`` is an int or None (the dispatch layer renders None
    as ``"—"`` in the Rich table).
    """
    config = _load_config(char_dir)
    rows: List[dict] = []
    for costume in _costume_names(char_dir):
        rows.append(
            {
                "character": character,
                "costume": costume,
                "variant_count": _count_variants(char_dir, costume),
                "picked_variant": _picked_variant(config, costume),
            }
        )
    return rows


def run_list(
    character: Optional[str] = None,
    *,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> List[dict]:
    """Return a list of costume rows.

    Args:
        character: If given, list that character's costumes only. If
            omitted, list costumes across every character under the
            resolved VNCCS state directory.
        comfy_path: Optional override for COMFY_PATH.
        state_dir: Optional override for the VNCCS state directory
            (precedence: this arg > VNCCS_STATE_DIR env >
            ``<comfy>/output/VN_CharacterCreatorSuit``).

    Returns:
        A list of dicts: ``{character, costume, variant_count,
        picked_variant}``. Sorted by character then costume, with
        ``Naked`` always first within each character (preserved from
        :func:`_costume_names`).

    Raises:
        VnccsPathError: COMFY_PATH unresolvable (exit 6).
        VnccsNotFoundError: ``character`` given but directory missing
            (exit 5). When ``character`` is omitted, a missing state
            root simply yields ``[]`` — that's not an error (fresh VNCCS
            install with no characters yet).
    """
    state_root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)

    if character is not None:
        char_dir = state_root / character
        if not char_dir.is_dir():
            raise VnccsNotFoundError(
                f"Character not found: {character!r}",
                detail=(
                    f"Expected directory at {char_dir}. Create the "
                    "character first with `vnccs character create NAME`."
                ),
            )
        return _costume_rows_for_character(char_dir, character)

    # All characters.
    if not state_root.is_dir():
        return []

    rows: List[dict] = []
    try:
        character_dirs = sorted(
            p for p in state_root.iterdir() if p.is_dir()
        )
    except OSError:
        return []

    for char_dir in character_dirs:
        rows.extend(_costume_rows_for_character(char_dir, char_dir.name))
    return rows
