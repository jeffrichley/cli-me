"""Logic for `vnccs emotion preview CHARACTER --emotion TYPE`.

Reveals the bundled pre-rendered preview image that VNCCS ships to
illustrate each emotion. These live at:

    <VNCCS_INSTALL>/emotions-config/images/<safe_name>.<ext>

where ``safe_name`` is the ``safe_name`` field from
``emotions-config/emotions.json`` (e.g. ``angry``, ``radiant-smile``).
Filenames are lowercase and hyphens are preserved literally.

Pure filesystem — no HTTP. The CHARACTER argument is accepted for API
symmetry with the rest of the ``emotion`` group but doesn't affect the
resolved path (the preview images are bundled with the node pack, not
per-character). We do validate the character exists before returning
so the caller gets a sensible error when they typo the name.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from vnccs_cli.backend import (
    VnccsNotFoundError,
    get_vnccs_install_dir,
    get_vnccs_state_dir,
)

# Image extensions we'll accept for a preview. The bundled images-dir
# ships ``.png`` in practice; we tolerate the common alternatives in
# case upstream adds them later.
PREVIEW_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def _emotions_images_dir(vnccs_install: Path) -> Path:
    """Return ``<VNCCS>/emotions-config/images/``."""
    return vnccs_install / "emotions-config" / "images"


def _known_emotions(images_dir: Path) -> List[str]:
    """Every bundled emotion (derived from filename stems in images/)."""
    if not images_dir.is_dir():
        return []
    names: List[str] = []
    try:
        for entry in images_dir.iterdir():
            if entry.is_file() and entry.suffix.lower() in PREVIEW_EXTENSIONS:
                names.append(entry.stem)
    except OSError:
        return []
    return sorted(set(names))


def _resolve_preview(images_dir: Path, emotion: str) -> Optional[Path]:
    """Return the preview file for ``emotion`` (trying each extension)."""
    for ext in PREVIEW_EXTENSIONS:
        candidate = images_dir / f"{emotion}{ext}"
        if candidate.is_file():
            return candidate
    return None


def run_preview(
    character: str,
    *,
    emotion: str,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> dict:
    """Return the path to the bundled preview image for ``emotion``.

    Args:
        character: Character directory name. Used only to fail fast with
            a clear error if the user typo'd the name; does not affect
            the returned preview (previews are bundled, not per-character).
        emotion: Emotion ``safe_name`` (matches a file stem under
            ``<VNCCS>/emotions-config/images/``; e.g. ``angry``).
        comfy_path: Optional override for COMFY_PATH.

    Returns:
        Dict: ``{emotion, path, exists}`` where ``path`` is the absolute
        string path to the preview (or the expected ``.png`` path if
        the preview is missing and ``exists`` is False).

        NOTE: If ``emotion`` is unknown (no file with that stem in the
        bundled ``images/`` dir), this function raises — the returned
        ``exists=False`` is only for the rare edge case of a known
        stem whose file disappears between ``iterdir`` and ``is_file``.

    Raises:
        VnccsPathError: COMFY_PATH unresolvable or VNCCS not installed
            (exit 6).
        VnccsNotFoundError: character directory missing, or emotion
            unknown in the bundled emotions-config (exit 5).
    """
    state_root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)
    char_dir = state_root / character
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {character!r}",
            detail=f"Expected directory at {char_dir}.",
        )

    vnccs_install = get_vnccs_install_dir(comfy_path)
    images_dir = _emotions_images_dir(vnccs_install)

    known = _known_emotions(images_dir)
    if not known:
        raise VnccsNotFoundError(
            "No bundled emotion previews available",
            detail=(
                f"Expected at least one image under {images_dir}. The "
                "VNCCS node pack may be partially installed — re-install "
                "with `comfyui custom-nodes install ...`."
            ),
        )

    if emotion not in known:
        # Hint a few close matches. Simple substring prefix for now.
        hint_candidates = [n for n in known if n.startswith(emotion[:3])][:5]
        hint = f" Did you mean: {', '.join(hint_candidates)}?" if hint_candidates else ""
        raise VnccsNotFoundError(
            f"Unknown emotion: {emotion!r}",
            detail=(
                f"Not present in {images_dir}. "
                f"Run `vnccs emotion preview --help` or list bundled emotions."
                f"{hint}"
            ),
        )

    preview = _resolve_preview(images_dir, emotion)
    return {
        "emotion": emotion,
        "path": str(preview) if preview else str(images_dir / f"{emotion}.png"),
        "exists": preview is not None,
    }
