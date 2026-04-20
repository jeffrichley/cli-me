"""Logic for `vnccs dataset preview` — dry-run of what `dataset export` would produce.

Pure filesystem inspection. No ComfyUI HTTP calls, no workflow submission,
no file writes. Given a character name and (optional) game-name prefix,
returns a plain dict describing what a subsequent `dataset export` would
write into the kohya-ss-compatible `<character>/lora/` directory.

The dispatch layer (``vnccs_cli.dataset``) turns that dict into either a
Rich-table summary or a JSON blob for agents to parse.

Layout reference: ``references/source-analysis/state-management.md``.
VNCCS's ``DatasetGenerator.generate_dataset`` walks BOTH:

- ``<character>/Faces/<costume>/<emotion>/face_*.png`` (portrait training pairs)
- ``<character>/Sprites/<costume>/<emotion>/sprite_*.png`` (full-body pairs)

and writes one ``.png`` + ``.txt`` pair per source file into
``<character>/lora/`` with name ``<costume>_<emotion>_<original>``. Preview
must count both trees — covering only ``Sprites/`` would under-count any
character that was run through stage 3 (emotions → Faces) but not yet
stage 4 (sprites), and hide all face captions from the sample list.

Caption prefix = ``<game_name>_<character_info.name>`` where
``character_info.name`` comes from ``<character>_config.json`` (falls back
to the directory name when absent). Matches upstream
``dataset_generator.py:128-132``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from vnccs_cli.backend import VnccsNotFoundError, get_vnccs_state_dir

DEFAULT_GAME_NAME = "VN"
FACE_PREFIX = "face_"
SPRITE_PREFIX = "sprite_"
PNG_SUFFIX = ".png"
SAMPLE_LIMIT = 10


def _iter_image_pngs(root: Path, prefix: str) -> List[Path]:
    """Walk ``<root>/<costume>/<emotion>/`` and collect every ``<prefix>*.png``.

    Returns a sorted list (deterministic ordering so the sample list is
    stable across runs — agents can rely on "first N" being the same N).
    Mirrors the upstream ``DatasetGenerator.generate_dataset`` filter
    (startswith(prefix), not .txt). Our ``.png`` guard is a tightening:
    VNCCS only writes PNGs in these trees, and a non-.png file under
    ``Sprites/`` would not be copied by export either.
    """
    if not root.is_dir():
        return []

    found: List[Path] = []
    for costume_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for emotion_dir in sorted(p for p in costume_dir.iterdir() if p.is_dir()):
            for png in sorted(emotion_dir.iterdir()):
                if not png.is_file():
                    continue
                name = png.name
                if name.startswith(prefix) and name.endswith(PNG_SUFFIX):
                    found.append(png)
    return found


def _load_character_info_name(char_dir: Path, fallback: str) -> str:
    """Read ``character_info.name`` from ``<character>_config.json``.

    Matches ``dataset_generator.py:128-132``: falls back to the directory
    name (``fallback``) if the config is missing, unreadable, or doesn't
    carry a ``character_info.name`` key. This is the single point where
    the wrapper's preview must agree with upstream export — a renamed
    character (dir ``aria_v2`` with config name ``Aria``) gets captions
    prefixed ``VN_Aria``, not ``VN_aria_v2``.
    """
    config_file = char_dir / f"{char_dir.name}_config.json"
    if not config_file.is_file():
        return fallback
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    info = data.get("character_info") if isinstance(data, dict) else None
    if isinstance(info, dict):
        name = info.get("name")
        if isinstance(name, str) and name:
            return name
    return fallback


def _output_layout(
    character: str,
    character_name: str,
    game_name: str,
    face_count: int,
    sprite_count: int,
) -> dict:
    """Describe the would-be export layout without committing to file writes.

    Kohya-ss convention is one flat directory per "concept"; VNCCS dumps
    everything into ``<character>/lora/`` (lowercase — upstream source at
    ``dataset_generator.py:134``, NOT ``Lora/`` as the README claims).
    Filenames are ``<costume>_<emotion>_<original>`` preserving the
    source's ``face_<emotion>_NNNNN_.png`` or ``sprite_<emotion>_NNNNN_.png``
    shape, so the actual output is e.g.
    ``casual_happy_sprite_happy_00001_.{png|txt}``.
    """
    return {
        "lora_dir": f"{character}/lora/",
        "face_filename_pattern": "{costume}_{emotion}_face_{emotion}_NNNNN_.{png|txt}",
        "sprite_filename_pattern": "{costume}_{emotion}_sprite_{emotion}_NNNNN_.{png|txt}",
        "caption_prefix": f"{game_name}_{character_name}",
        "face_pairs": face_count,
        "sprite_pairs": sprite_count,
        "estimated_pairs": face_count + sprite_count,
    }


def _interleave_samples(faces: List[Path], sprites: List[Path], limit: int) -> List[str]:
    """Interleave face + sprite filenames so the sample list reflects both trees.

    Pattern: ``[face0, sprite0, face1, sprite1, ...]`` then remainders.
    This gives agents sanity-checking captions a view into BOTH training
    modalities within the top-N, rather than ``limit`` faces only.
    """
    samples: List[str] = []
    n = max(len(faces), len(sprites))
    for i in range(n):
        if i < len(faces):
            samples.append(faces[i].name)
            if len(samples) >= limit:
                break
        if i < len(sprites):
            samples.append(sprites[i].name)
            if len(samples) >= limit:
                break
    return samples


def run_preview(
    character: str,
    *,
    game_name: Optional[str] = None,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> dict:
    """Dry-run `dataset export` for ``character`` — return a plain dict.

    Args:
        character: Character name (must match an existing directory under
            the resolved VNCCS state directory).
        game_name: Optional kohya caption-prefix / folder tag; defaults to
            ``"VN"`` to match ``DatasetGenerator.INPUT_TYPES`` upstream.
        comfy_path: Optional override for COMFY_PATH.
        state_dir: Optional override for the VNCCS state directory
            (precedence: this arg > VNCCS_STATE_DIR env >
            ``<comfy>/output/VN_CharacterCreatorSuit``).

    Returns:
        dict with keys ``character``, ``character_name``, ``game_name``,
        ``face_count``, ``sprite_count``, ``pair_count``, ``caption_count``,
        ``output_layout``, ``samples`` (interleaved face/sprite filenames
        up to :data:`SAMPLE_LIMIT`), ``total_samples``.

    Raises:
        VnccsPathError: COMFY_PATH unresolvable (exit 6).
        VnccsNotFoundError: character directory missing OR the character
            has zero face AND zero sprite PNGs (exit 5). A character with
            faces but no sprites (or vice-versa) is VALID — export will
            produce a portrait-only or full-body-only LoRA dataset.
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

    face_pngs = _iter_image_pngs(char_dir / "Faces", FACE_PREFIX)
    sprite_pngs = _iter_image_pngs(char_dir / "Sprites", SPRITE_PREFIX)

    if not face_pngs and not sprite_pngs:
        raise VnccsNotFoundError(
            f"No training images found for character: {character!r}",
            detail=(
                f"Expected face_*.png under {char_dir / 'Faces'} AND/OR "
                f"sprite_*.png under {char_dir / 'Sprites'}. Run "
                "`vnccs emotion add` (generates Faces) and "
                "`vnccs sprite render` (generates Sprites) before exporting."
            ),
        )

    resolved_game = game_name if game_name is not None else DEFAULT_GAME_NAME
    character_name = _load_character_info_name(char_dir, fallback=character)

    face_count = len(face_pngs)
    sprite_count = len(sprite_pngs)
    pair_count = face_count + sprite_count
    # One caption .txt per image PNG — strict 1:1 per dataset_generator.py
    # (see references/techniques/sprites-and-datasets.md §"Output layout").
    caption_count = pair_count

    samples = _interleave_samples(face_pngs, sprite_pngs, SAMPLE_LIMIT)

    return {
        "character": character,
        "character_name": character_name,
        "game_name": resolved_game,
        "face_count": face_count,
        "sprite_count": sprite_count,
        "pair_count": pair_count,
        "caption_count": caption_count,
        "output_layout": _output_layout(
            character, character_name, resolved_game, face_count, sprite_count
        ),
        "samples": samples,
        "total_samples": pair_count,
    }


def format_json(result: dict) -> str:
    """Render a preview result as stable-shape JSON for agents.

    The JSON shape is the documented contract for ``--json`` output. Keep
    the key list in sync with the docstring on :func:`run_preview`.
    """
    payload = {
        "character": result["character"],
        "character_name": result["character_name"],
        "game_name": result["game_name"],
        "face_count": result["face_count"],
        "sprite_count": result["sprite_count"],
        "pair_count": result["pair_count"],
        "caption_count": result["caption_count"],
        "output_layout": result["output_layout"],
        "samples": result["samples"],
    }
    return json.dumps(payload, indent=2)
