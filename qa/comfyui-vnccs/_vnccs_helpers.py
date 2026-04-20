"""Assertion helpers for comfyui-vnccs QA tests.

Importable as ``from _vnccs_helpers import ...``. Lives outside conftest
because conftest is auto-loaded by pytest, not meant to be imported by
name (importlib mode breaks ``from conftest import ...``). Skill-prefixed
so it doesn't collide with other skills' helpers when the whole-suite runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence


# PNG magic bytes (8 bytes): matches real image readers' sniffing.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def make_fake_character_with_sprites(
    comfy_root: Path,
    character: str,
    *,
    costume: str = "casual",
    emotion: str = "happy",
    sprite_count: int = 5,
    extra_emotions: Optional[Iterable[str]] = None,
) -> Path:
    """Materialize a VNCCS character tree with fake sprite PNGs on disk.

    Creates ``<comfy>/output/VN_CharacterCreatorSuit/<character>/Sprites/
    <costume>/<emotion>/sprite_<emotion>_NNNNN_.png`` with ``sprite_count``
    files. Each PNG is a minimal 8-byte header — enough for "is this a
    PNG?" sniff checks without needing Pillow.

    Narrow helper named distinctly so it won't collide with
    ``make_fake_character`` if a sibling agent adds a broader helper.

    Args:
        comfy_root: Fake ComfyUI root (from the ``fake_comfy`` fixture).
        character: Character directory name.
        costume: Costume subdir name (default ``"casual"``).
        emotion: Emotion subdir name (default ``"happy"``).
        sprite_count: How many sprite PNGs to create (default ``5``).
        extra_emotions: Optional extra emotion subdirs (each gets one
            sprite PNG). Lets tests exercise multi-emotion totals without
            duplicating the whole helper.

    Returns:
        The character's on-disk directory (e.g. ``<comfy>/output/
        VN_CharacterCreatorSuit/<character>``).
    """
    char_dir = comfy_root / "output" / "VN_CharacterCreatorSuit" / character
    sprites = char_dir / "Sprites" / costume / emotion
    sprites.mkdir(parents=True, exist_ok=True)
    for i in range(1, sprite_count + 1):
        png = sprites / f"sprite_{emotion}_{i:05d}_.png"
        png.write_bytes(_PNG_MAGIC)

    if extra_emotions:
        for extra in extra_emotions:
            extra_dir = char_dir / "Sprites" / costume / extra
            extra_dir.mkdir(parents=True, exist_ok=True)
            (extra_dir / f"sprite_{extra}_00001_.png").write_bytes(_PNG_MAGIC)

    return char_dir


def make_empty_fake_character(comfy_root: Path, character: str) -> Path:
    """Create a character directory with no ``Sprites/`` tree at all.

    Used to exercise the "character exists but has zero sprites" branch
    of ``dataset preview`` — should raise ``VnccsNotFoundError`` (exit 5).
    """
    char_dir = comfy_root / "output" / "VN_CharacterCreatorSuit" / character
    char_dir.mkdir(parents=True, exist_ok=True)
    return char_dir


def make_fake_costumes_dir(
    comfy_root: Path,
    character: str,
    *,
    costumes: Optional[Mapping[str, dict]] = None,
    emotions: Optional[Sequence[str]] = None,
) -> Path:
    """Materialize a VNCCS character tree for clothing + emotion read-only tests.

    Builds ``<comfy>/output/VN_CharacterCreatorSuit/<character>/`` with:

      * ``<character>_config.json`` containing a ``costumes`` dict
      * ``Sheets/<costume>/neutral/sheet_neutral_NNNNN_.png`` (one per variant)
      * ``Sheets/<costume>/<emotion>/sheet_<emotion>_00001_.png`` for each emotion

    The "variant count" of a costume is the number of ``sheet_neutral_*.png``
    files under ``Sheets/<costume>/neutral/``. The "picked variant" is read
    from ``config["costumes"][<name>]["picked_variant"]`` — an integer
    matching the ``NNNNN`` sequence part of the chosen filename (or absent
    if no pick has been made).

    Narrow, distinctly-named helper so it won't collide with a broader
    ``make_fake_character`` if the sibling ``character list/show`` agent
    adds one.

    Args:
        comfy_root: Fake ComfyUI root (from the ``fake_comfy`` fixture).
        character: Character directory name.
        costumes: Mapping of costume name to options dict. Each options
            dict may contain ``variants`` (int, default 1), ``picked`` (int
            or None), plus any other costume metadata (top, bottom, etc.)
            which is written verbatim into the config. Default:
            ``{"casual": {"variants": 3, "picked": 2},
               "formal": {"variants": 1, "picked": None}}``.
        emotions: List of emotion subdirs to create under each costume.
            Default: ``("happy", "sad", "angry")``. Pass an empty tuple
            to only populate ``neutral/`` variants.

    Returns:
        The character's on-disk directory.
    """
    if costumes is None:
        costumes = {
            "casual": {"variants": 3, "picked": 2},
            "formal": {"variants": 1, "picked": None},
        }
    if emotions is None:
        emotions = ("happy", "sad", "angry")

    char_dir = comfy_root / "output" / "VN_CharacterCreatorSuit" / character
    (char_dir / "Sheets").mkdir(parents=True, exist_ok=True)

    config_costumes: dict = {}
    for costume_name, opts in costumes.items():
        variants = int(opts.get("variants", 1))
        picked = opts.get("picked")

        neutral_dir = char_dir / "Sheets" / costume_name / "neutral"
        neutral_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, variants + 1):
            (neutral_dir / f"sheet_neutral_{i:05d}_.png").write_bytes(_PNG_MAGIC)

        for emotion in emotions:
            emotion_dir = char_dir / "Sheets" / costume_name / emotion
            emotion_dir.mkdir(parents=True, exist_ok=True)
            (emotion_dir / f"sheet_{emotion}_00001_.png").write_bytes(_PNG_MAGIC)

        # Copy any extra metadata (top, bottom, etc.) verbatim, strip helper keys.
        entry = {k: v for k, v in opts.items() if k not in {"variants", "picked"}}
        if picked is not None:
            entry["picked_variant"] = int(picked)
        config_costumes[costume_name] = entry

    config = {
        "character_info": {"name": character, "sex": "female", "age": 20},
        "folder_structure": {
            "main_directories": ["Sprites", "Faces", "Sheets"],
            "emotions": ["neutral"],
        },
        "character_path": str(char_dir),
        "config_version": "2.0",
        "costumes": config_costumes,
    }
    (char_dir / f"{character}_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
    return char_dir


def make_fake_emotion_preview(
    comfy_root: Path,
    *,
    emotion: str,
    size_bytes: int = 32,
) -> Path:
    """Place a fake bundled emotion preview image under VNCCS's emotions-config.

    Writes ``<comfy>/custom_nodes/ComfyUI_VNCCS/emotions-config/images/
    <emotion>.png`` with a minimal PNG header padded to ``size_bytes``.
    Returns the absolute path to the preview.

    The ``fake_comfy`` fixture already creates the ``emotions-config/images``
    dir; this helper just writes a file into it.
    """
    img_dir = (
        comfy_root
        / "custom_nodes"
        / "ComfyUI_VNCCS"
        / "emotions-config"
        / "images"
    )
    img_dir.mkdir(parents=True, exist_ok=True)
    payload = _PNG_MAGIC + (b"\x00" * max(0, size_bytes - len(_PNG_MAGIC)))
    png = img_dir / f"{emotion}.png"
    png.write_bytes(payload)
    return png


def assert_workflow_sha256(path: Path, expected: str) -> None:
    """Assert a bundled workflow JSON matches its pinned SHA-256.

    Catches accidental modifications to bundled workflows (they should be
    byte-identical to the pinned upstream commit). See
    scripts/workflows/README.md for the expected hashes.
    """
    assert path.exists(), f"Bundled workflow missing: {path}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, (
        f"Workflow {path.name} has sha256 {actual}; expected {expected}. "
        "Bundled workflows should be byte-identical to the pinned upstream "
        "commit. Has the file been modified locally?"
    )


def assert_valid_json(path: Path) -> dict:
    """Assert a file contains parseable JSON and return the parsed dict."""
    assert path.exists(), f"File missing: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise AssertionError(f"Not valid JSON: {path} — {e}") from e


def assert_workflow_has_class_type(workflow: dict, class_type: str) -> None:
    """Assert a class_type string appears somewhere in a workflow JSON tree.

    Walks the workflow dict (including nested subgraphs in GUI-format
    workflows) looking for any node with the given class_type.
    """
    found = []

    def walk(x):
        if isinstance(x, dict):
            for k in ("class_type", "type"):
                v = x.get(k)
                if isinstance(v, str) and v == class_type:
                    found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(workflow)
    assert found, (
        f"No node with class_type={class_type!r} found in workflow. "
        f"(Searched entire tree including subgraphs.)"
    )
