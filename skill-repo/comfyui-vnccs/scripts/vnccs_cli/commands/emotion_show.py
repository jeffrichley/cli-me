"""Logic for `vnccs emotion show CHARACTER --emotion TYPE [--costume NAME]`.

Inspects the most-recent rendered emotion sheet for (character, costume,
emotion). Pure filesystem — no HTTP. Follows the upstream
``utils.load_character_sheet`` convention: pick the sheet with the
highest ``NNNNN`` sequence under ``Sheets/<costume>/<emotion>/``.

If ``--costume`` is omitted and the emotion exists in exactly one
costume, that one is used. If it exists in multiple costumes, the
behaviour is deterministic: we raise ``VnccsNotFoundError`` asking the
caller to disambiguate (better than silently picking one).

Layout reference: ``references/source-analysis/state-management.md``.
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import List, Optional

from vnccs_cli.backend import VnccsNotFoundError, get_comfy_path

VNCCS_STATE_SUBDIR = "VN_CharacterCreatorSuit"


def _state_root(comfy_path: Path) -> Path:
    return comfy_path / "output" / VNCCS_STATE_SUBDIR


def _character_dir(comfy_path: Path, character: str) -> Path:
    return _state_root(comfy_path) / character


def _sheet_seq_regex(emotion: str) -> re.Pattern:
    """Regex matching ``sheet_<emotion>_NNNNN_.png`` with the sequence captured.

    Escapes ``emotion`` so hyphens / dots / regex meta-chars in emotion
    names (e.g. ``radiant-smile``) are matched literally.
    """
    return re.compile(rf"^sheet_{re.escape(emotion)}_(\d+)_?\.png$")


def _latest_sheet(emotion_dir: Path, emotion: str) -> Optional[Path]:
    """Return the sheet PNG with the highest ``NNNNN`` in ``emotion_dir``.

    Returns None if no matching files exist. Ignores files that don't
    match the expected pattern so non-VNCCS files won't confuse the pick.
    """
    pattern = _sheet_seq_regex(emotion)
    best: Optional[tuple[int, Path]] = None
    try:
        for entry in emotion_dir.iterdir():
            if not entry.is_file():
                continue
            match = pattern.match(entry.name)
            if not match:
                continue
            seq = int(match.group(1))
            if best is None or seq > best[0]:
                best = (seq, entry)
    except OSError:
        return None
    return best[1] if best else None


def _costumes_with_emotion(char_dir: Path, emotion: str) -> List[str]:
    """Costumes whose ``Sheets/<costume>/<emotion>/`` has at least one sheet PNG."""
    sheets_root = char_dir / "Sheets"
    if not sheets_root.is_dir():
        return []
    pattern = _sheet_seq_regex(emotion)
    result: List[str] = []
    try:
        costume_dirs = sorted(p for p in sheets_root.iterdir() if p.is_dir())
    except OSError:
        return []
    for costume_dir in costume_dirs:
        emotion_dir = costume_dir / emotion
        if not emotion_dir.is_dir():
            continue
        try:
            has_sheet = any(
                entry.is_file() and pattern.match(entry.name)
                for entry in emotion_dir.iterdir()
            )
        except OSError:
            continue
        if has_sheet:
            result.append(costume_dir.name)
    return result


def run_show(
    character: str,
    *,
    emotion: str,
    costume: Optional[str] = None,
    comfy_path: Optional[str] = None,
) -> dict:
    """Inspect the latest rendered sheet for (character, costume, emotion).

    Args:
        character: Character directory name.
        emotion: Emotion name (matches the ``Sheets/<costume>/<emotion>/``
            subdirectory name; e.g. ``happy``, ``radiant-smile``).
        costume: Optional costume name. If omitted and the emotion exists
            under exactly one costume, that costume is used. If ambiguous,
            raises ``VnccsNotFoundError`` listing the candidates.
        comfy_path: Optional override for COMFY_PATH.

    Returns:
        Dict with keys ``character``, ``costume``, ``emotion``, ``path``
        (absolute str), ``size`` (int bytes), ``created`` (ISO-8601 str
        from the file's mtime — the upstream uses ``NNNNN`` sequences as
        its "when" signal and doesn't record wall-clock; mtime is the
        best we have without parsing ComfyUI history).

    Raises:
        VnccsPathError: COMFY_PATH unresolvable (exit 6).
        VnccsNotFoundError: character, costume, or emotion-sheet file
            missing, OR ``costume`` unspecified and emotion ambiguous
            across costumes (exit 5).
    """
    comfy = get_comfy_path(comfy_path)
    char_dir = _character_dir(comfy, character)
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {character!r}",
            detail=f"Expected directory at {char_dir}.",
        )

    resolved_costume = costume
    if resolved_costume is None:
        candidates = _costumes_with_emotion(char_dir, emotion)
        if not candidates:
            raise VnccsNotFoundError(
                f"No sheets for emotion {emotion!r} under character {character!r}",
                detail=(
                    f"Expected at least one "
                    f"{char_dir}/Sheets/<costume>/{emotion}/sheet_{emotion}_*.png. "
                    "Generate with `vnccs emotion add`."
                ),
            )
        if len(candidates) > 1:
            raise VnccsNotFoundError(
                f"Emotion {emotion!r} exists in multiple costumes for {character!r}",
                detail=(
                    f"Found in: {', '.join(candidates)}. "
                    "Disambiguate with --costume NAME."
                ),
            )
        resolved_costume = candidates[0]

    emotion_dir = char_dir / "Sheets" / resolved_costume / emotion
    if not emotion_dir.is_dir():
        raise VnccsNotFoundError(
            f"Emotion directory missing: {resolved_costume}/{emotion}",
            detail=f"Expected at {emotion_dir}.",
        )

    sheet = _latest_sheet(emotion_dir, emotion)
    if sheet is None:
        raise VnccsNotFoundError(
            f"No rendered sheet for emotion {emotion!r} "
            f"under {character}/{resolved_costume}/",
            detail=(
                f"Expected at least one sheet_{emotion}_NNNNN_.png in {emotion_dir}. "
                "Generate with `vnccs emotion add`."
            ),
        )

    try:
        stat = sheet.stat()
    except OSError as e:
        raise VnccsNotFoundError(
            f"Could not stat emotion sheet: {sheet}",
            detail=str(e),
        ) from e

    created = _dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    return {
        "character": character,
        "costume": resolved_costume,
        "emotion": emotion,
        "path": str(sheet),
        "size": stat.st_size,
        "created": created,
    }
