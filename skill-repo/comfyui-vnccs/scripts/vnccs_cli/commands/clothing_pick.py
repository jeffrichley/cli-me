"""Logic for `vnccs clothing pick` — record the chosen variant of a costume.

Writes ``config["costumes"][<costume>]["picked_variant"] = N`` to the
character's ``<character>_config.json``. No ComfyUI contact — pure
filesystem.

Validates that variant N actually exists on disk (i.e.
``sheet_neutral_0000N_.png`` is present under ``Sheets/<costume>/neutral/``)
to avoid writing a pick that points at a nonexistent file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from vnccs_cli.backend import (
    VnccsError,
    VnccsNotFoundError,
    VnccsValidationError,
    get_vnccs_state_dir,
)

SHEET_NEUTRAL_PATTERN = re.compile(r"^sheet_neutral_(\d+)_?\.png$")


def _available_variants(neutral_dir: Path) -> list[int]:
    """Enumerate NNNNN sequence numbers of existing variant files (sorted)."""
    if not neutral_dir.is_dir():
        return []
    variants: list[int] = []
    try:
        for entry in neutral_dir.iterdir():
            if not entry.is_file():
                continue
            m = SHEET_NEUTRAL_PATTERN.match(entry.name)
            if m:
                variants.append(int(m.group(1)))
    except OSError:
        return []
    return sorted(variants)


def run_pick(
    character: str,
    costume: str,
    variant: int,
    *,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> dict:
    """Record ``costumes[<costume>].picked_variant = variant`` in config.

    Returns ``{character, costume, picked_variant, available_variants, config_path}``.

    Raises:
        VnccsError (exit 1): empty args.
        VnccsValidationError (exit 3): variant < 1 OR the variant file
            doesn't exist on disk.
        VnccsNotFoundError (exit 5): character / costume / config missing.
    """
    if not character:
        raise VnccsError("character is required")
    if not costume:
        raise VnccsError("--name (costume) is required")
    if variant < 1:
        raise VnccsValidationError(
            f"--variant must be >= 1 (got {variant})"
        )

    root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)
    char_dir = root / character
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {character}",
            detail=f"Expected directory {char_dir}.",
        )
    neutral_dir = char_dir / "Sheets" / costume / "neutral"
    if not neutral_dir.is_dir():
        raise VnccsNotFoundError(
            f"Costume not found: {character}/{costume}",
            detail=f"Expected directory {neutral_dir}.",
        )

    available = _available_variants(neutral_dir)
    if variant not in available:
        raise VnccsValidationError(
            f"Variant {variant} does not exist for {character}/{costume}",
            detail=(
                f"Available variants: {available!r}. Generate more with "
                f"`vnccs clothing add {character} --name {costume} --variants N`."
            ),
        )

    config_file = char_dir / f"{char_dir.name}_config.json"
    if not config_file.is_file():
        raise VnccsNotFoundError(
            f"Config file missing: {config_file}",
            detail=(
                "The character config must exist to record a pick. "
                "Did the character finish stage 1?"
            ),
        )
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VnccsValidationError(
            f"Config file is not valid JSON: {config_file}",
            detail=str(exc),
        ) from exc

    costumes = data.setdefault("costumes", {})
    entry = costumes.setdefault(costume, {})
    if not isinstance(entry, dict):
        # Stale schema — replace with a minimal dict
        entry = {}
        costumes[costume] = entry
    entry["picked_variant"] = int(variant)

    config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return {
        "character": character,
        "costume": costume,
        "picked_variant": variant,
        "available_variants": available,
        "config_path": str(config_file),
    }
