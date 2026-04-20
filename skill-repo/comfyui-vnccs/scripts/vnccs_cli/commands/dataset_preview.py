"""Logic for `vnccs dataset preview` — dry-run of what `dataset export` would produce.

Pure filesystem inspection. No ComfyUI HTTP calls, no workflow submission,
no file writes. Given a character name and (optional) game-name prefix,
returns a plain dict describing what a subsequent `dataset export` would
write into the kohya-ss-compatible `<character>/lora/` directory.

The dispatch layer (``vnccs_cli.dataset``) turns that dict into either a
Rich-table summary or a JSON blob for agents to parse.

Layout reference: ``references/source-analysis/state-management.md``
(sprites live at ``<comfy_output>/VN_CharacterCreatorSuit/<character>/Sprites/<costume>/<emotion>/sprite_*.png``).
Caption + filename conventions: see ``references/techniques/sprites-and-datasets.md``
and the upstream ``nodes/dataset_generator.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from vnccs_cli.backend import VnccsNotFoundError, get_comfy_path

VNCCS_STATE_SUBDIR = "VN_CharacterCreatorSuit"
DEFAULT_GAME_NAME = "VN"
SPRITE_PREFIX = "sprite_"
PNG_SUFFIX = ".png"
SAMPLE_LIMIT = 10


def vnccs_state_root(comfy_path: Path) -> Path:
    """Return the VNCCS state root: ``<comfy>/output/VN_CharacterCreatorSuit``.

    Matches ``utils.base_output_dir()`` in the upstream node pack. See
    references/source-analysis/state-management.md §"Root directory".
    """
    return comfy_path / "output" / VNCCS_STATE_SUBDIR


def character_dir(comfy_path: Path, character: str) -> Path:
    """Resolved on-disk directory for a VNCCS character."""
    return vnccs_state_root(comfy_path) / character


def _iter_sprite_pngs(sprites_root: Path) -> List[Path]:
    """Walk ``<char>/Sprites/<costume>/<emotion>/`` and collect every sprite PNG.

    Returns a sorted list (deterministic ordering so the sample list is
    stable across runs — agents can rely on "first N" being the same N).
    Accepts any ``sprite_*.png`` file; matches the upstream
    ``DatasetGenerator.generate_dataset`` filter (``startswith("sprite_")``
    and not ``.txt``).
    """
    if not sprites_root.is_dir():
        return []

    found: List[Path] = []
    for costume_dir in sorted(p for p in sprites_root.iterdir() if p.is_dir()):
        for emotion_dir in sorted(p for p in costume_dir.iterdir() if p.is_dir()):
            for png in sorted(emotion_dir.iterdir()):
                if not png.is_file():
                    continue
                name = png.name
                if name.startswith(SPRITE_PREFIX) and name.endswith(PNG_SUFFIX):
                    found.append(png)
    return found


def _output_layout(character: str, game_name: str, sprite_count: int) -> dict:
    """Describe the would-be export layout without committing to file writes.

    Kohya-ss convention is one flat directory per "concept"; VNCCS dumps
    everything into ``<character>/lora/`` with filenames
    ``<costume>_<emotion>_<original>.{png,txt}``. The caption prefix is
    ``<game_name>_<character>``, e.g. ``MyVN_Aria``.
    """
    return {
        "lora_dir": f"{character}/lora/",
        "filename_pattern": "{costume}_{emotion}_sprite_{n}.{png|txt}",
        "caption_prefix": f"{game_name}_{character}",
        "estimated_pairs": sprite_count,
    }


def run_preview(
    character: str,
    *,
    game_name: Optional[str] = None,
    comfy_path: Optional[str] = None,
) -> dict:
    """Dry-run `dataset export` for ``character`` — return a plain dict.

    Args:
        character: Character name (must match an existing directory under
            ``<comfy>/output/VN_CharacterCreatorSuit/``).
        game_name: Optional kohya caption-prefix / folder tag; defaults to
            ``"VN"`` to match ``DatasetGenerator.INPUT_TYPES`` upstream.
        comfy_path: Optional override for COMFY_PATH (passes through to
            :func:`backend.get_comfy_path`).

    Returns:
        dict with keys ``character``, ``game_name``, ``sprite_count``,
        ``caption_count``, ``output_layout``, ``sprite_samples`` (list of
        filenames, up to :data:`SAMPLE_LIMIT`), ``total_samples``.

    Raises:
        VnccsPathError: COMFY_PATH unresolvable (exit 6).
        VnccsNotFoundError: character directory missing or has zero
            sprite PNGs under ``Sprites/`` (exit 5).
    """
    resolved_comfy = get_comfy_path(comfy_path)
    char_dir = character_dir(resolved_comfy, character)

    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {character!r}",
            detail=(
                f"Expected directory at {char_dir}. Create the character "
                "first with `vnccs character create NAME`."
            ),
        )

    sprites_root = char_dir / "Sprites"
    sprite_pngs = _iter_sprite_pngs(sprites_root)

    if not sprite_pngs:
        raise VnccsNotFoundError(
            f"No sprites found for character: {character!r}",
            detail=(
                f"Expected sprite PNGs under {sprites_root}. Run "
                "`vnccs sprite render NAME` to generate them before exporting."
            ),
        )

    resolved_game = game_name if game_name is not None else DEFAULT_GAME_NAME
    sprite_count = len(sprite_pngs)
    # One caption .txt per sprite PNG — strict 1:1 per dataset_generator.py
    # (see references/techniques/sprites-and-datasets.md §"Output layout").
    caption_count = sprite_count

    samples = [p.name for p in sprite_pngs[:SAMPLE_LIMIT]]

    return {
        "character": character,
        "game_name": resolved_game,
        "sprite_count": sprite_count,
        "caption_count": caption_count,
        "output_layout": _output_layout(character, resolved_game, sprite_count),
        "sprite_samples": samples,
        "total_samples": sprite_count,
    }


def format_json(result: dict) -> str:
    """Render a preview result as stable-shape JSON for agents.

    The JSON shape is the documented contract for ``--json`` output. Keep
    the key list in sync with the docstring on :func:`run_preview`.
    """
    payload = {
        "character": result["character"],
        "sprite_count": result["sprite_count"],
        "caption_count": result["caption_count"],
        "output_layout": result["output_layout"],
        "sprite_samples": result["sprite_samples"],
    }
    return json.dumps(payload, indent=2)
