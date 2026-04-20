"""Logic for `vnccs clothing add` — stage 2 costume generation.

Submits the bundled Step2 V1SDXL legacy clothing workflow once per
``--variants N``. Each submission uses a distinct seed so VNCCS's
downstream samplers produce different variants. Validates that the
target character exists on disk before submitting (exit 5 if missing).
"""

from __future__ import annotations

import random
import time
from typing import Any, Optional

from vnccs_cli.backend import (
    VnccsError,
    VnccsNotFoundError,
    VnccsValidationError,
    VnccsWorkflowError,
    get_vnccs_state_dir,
    load_api_workflow,
    patch_workflow_node,
    submit_workflow,
    wait_for_prompt,
)

STEP2_LEGACY_WORKFLOW = "V1SDXL/VN_Step2_ClothesChanger_v5_api.json"


def _assert_character_exists(
    character: str,
    *,
    comfy_path: Optional[str],
    state_dir: Optional[str],
) -> None:
    root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)
    char_dir = root / character
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {character}",
            detail=(
                f"Expected directory {char_dir}. Create one with "
                "`vnccs character create`."
            ),
        )


def _build_workflow(
    character: str,
    costume: str,
    description: str,
    *,
    seed: int,
) -> dict:
    workflow = load_api_workflow(STEP2_LEGACY_WORKFLOW)

    # Route the single `--description` to `top` (the most visible clothing
    # slot in VN sprites). Advanced users who need finer slot control can
    # drop to the raw workflow.
    inputs: dict[str, Any] = {
        "character": character,
        "new_costume_name": costume,
        "top": description,
    }
    patched = patch_workflow_node(
        workflow, class_type="CharacterAssetSelector", inputs=inputs
    )
    if patched == 0:
        raise VnccsWorkflowError(
            "CharacterAssetSelector node missing from Step2 workflow.",
            detail=(
                f"Bundled workflow {STEP2_LEGACY_WORKFLOW} appears corrupt — "
                "re-install the comfyui-vnccs skill."
            ),
        )
    # Seed: inject into the CharacterCreator-like node if present (same
    # CharacterCreator node appears in Step2 workflow to carry the character
    # settings); otherwise this is a best-effort and VNCCS uses its own seed.
    patch_workflow_node(
        workflow, class_type="CharacterCreator", inputs={"seed": int(seed)}
    )
    return workflow


def run_add(
    character: str,
    costume: str,
    description: str,
    *,
    variants: int = 1,
    seed: Optional[int] = None,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
    url: Optional[str] = None,
    wait: bool = True,
    timeout: float = 600.0,
) -> dict:
    """Submit the Step2 clothing workflow ``variants`` times for ``character``.

    Returns ``{character, costume, variants: int, submissions: [dict, ...]}``.
    Each submission dict mirrors ``submit_workflow``'s return with an
    optional ``history`` entry.
    """
    if not character:
        raise VnccsError("character is required")
    if not costume:
        raise VnccsError("--name (costume) is required")
    if variants < 1:
        raise VnccsValidationError(
            f"--variants must be >= 1 (got {variants})"
        )

    _assert_character_exists(
        character, comfy_path=comfy_path, state_dir=state_dir
    )

    rng = random.Random(seed)
    submissions: list[dict] = []
    for i in range(variants):
        # Derive a distinct seed per variant: explicit base seed → deterministic
        # sequence; no base seed → time-mixed random ints.
        if seed is None:
            variant_seed = rng.randrange(0, 2**31 - 1)
        else:
            variant_seed = int(seed) + i

        workflow = _build_workflow(
            character, costume, description, seed=variant_seed
        )
        result = submit_workflow(workflow, url=url)
        if wait and result.get("prompt_id"):
            entry = wait_for_prompt(
                result["prompt_id"], url=url, timeout=timeout
            )
            result = dict(result)
            result["history"] = entry
        result["variant_index"] = i
        result["variant_seed"] = variant_seed
        submissions.append(result)

    return {
        "character": character,
        "costume": costume,
        "variants": variants,
        "submissions": submissions,
    }
