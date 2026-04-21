"""Logic for `vnccs character create` — stage 1 character sheet generation.

Submits the bundled **V1SDXL legacy** character-sheet workflow (stable
path). Patches the ``CharacterCreator`` node + applies the
live-environment defaults discovered during integration testing:

  - ``existing_character`` must point at a name that's already in the
    CharacterCreator dropdown. The wrapper calls ``/vnccs/create`` first
    so the new name is registered before submission.
  - Workflow's default LoadImage references a stale ``short_body6.png``;
    we patch it to the bundled ``CharacterSheetTemplate.png`` (auto-copied
    into ComfyUI's ``input/`` dir) unless ``--pose`` overrides.
  - VNCCS_RMBG2's default ``background='Color'`` is no longer a valid
    choice (current valid set: Alpha/Green/Blue). We patch to ``Green``
    so the downstream VNCCSChromaKey node has the right background to
    key out — Alpha breaks downstream RGB-only convolutions.

Uses the SDXL legacy workflow by default because Step3 QWEN has the
upstream broken-nodes bug — to keep the full pipeline consistent,
stages 1-4 all live on the V1SDXL path until upstream ships the missing
Python classes. Step1.1 clone is the exception: it uses QWEN because
QWEN's strength is reference-image cloning (and Step1.1 doesn't depend
on the broken Step3 nodes).
"""

from __future__ import annotations

from typing import Any, Optional

from vnccs_cli import backend
from vnccs_cli.backend import (
    VnccsError,
    VnccsWorkflowError,
    ensure_input_template,
    get_comfy_path,
    init_character_via_rest,
    load_api_workflow,
    patch_workflow_node,
    submit_workflow,
    wait_for_prompt,
)

# Workflow filename relative to scripts/workflows/api/.
STEP1_LEGACY_WORKFLOW = "V1SDXL/VN_Step1_CharSheetGenerator_v5_api.json"


def _build_workflow(
    name: str,
    description: str,
    *,
    pose: Optional[str] = None,
    seed: Optional[int] = None,
) -> dict:
    """Load Step1 SDXL workflow + patch user-supplied values. Pure function."""
    workflow = load_api_workflow(STEP1_LEGACY_WORKFLOW)

    inputs: dict[str, Any] = {
        "new_character_name": name,
        # ``existing_character`` is a dropdown widget populated from disk
        # by VNCCS at /object_info time. After init_character_via_rest()
        # creates the directory, NAME is in the dropdown — patching it
        # here makes the workflow address the right output paths.
        "existing_character": name,
        "additional_details": description,
    }
    if seed is not None:
        inputs["seed"] = int(seed)

    patched = patch_workflow_node(
        workflow, class_type="CharacterCreator", inputs=inputs
    )
    if patched == 0:
        raise VnccsWorkflowError(
            "CharacterCreator node missing from Step1 workflow.",
            detail=(
                f"Bundled workflow {STEP1_LEGACY_WORKFLOW} appears corrupt — "
                "re-install the comfyui-vnccs skill."
            ),
        )

    # Pose ref image: --pose overrides; otherwise the bundled VNCCS
    # CharacterSheetTemplate.png (which the wrapper auto-copies into
    # ComfyUI/input/ via ensure_input_template).
    pose_image = f"{pose}.png" if pose else "CharacterSheetTemplate.png"
    pose_patched = patch_workflow_node(
        workflow,
        class_type="LoadImage",
        title="Character sheet",
        inputs={"image": pose_image},
    )
    if pose_patched == 0:
        raise VnccsWorkflowError(
            "Character-sheet LoadImage node missing from Step1 workflow.",
            detail=(
                "Expected a LoadImage node titled 'Character sheet' that "
                "accepts a pose preset filename. Workflow may be out of "
                "sync with this wrapper."
            ),
        )

    # VNCCS_RMBG2 background default ``Color`` was removed in current VNCCS
    # node versions; valid choices are Alpha/Green/Blue. Use Green so the
    # downstream VNCCSChromaKey node can key it out (Alpha would feed RGBA
    # into a 3-channel conv and crash with channel-count mismatch).
    patch_workflow_node(
        workflow, class_type="VNCCS_RMBG2", inputs={"background": "Green"}
    )
    return workflow


def run_create(
    name: str,
    description: str,
    *,
    pose: Optional[str] = None,
    seed: Optional[int] = None,
    comfy_path: Optional[str] = None,
    url: Optional[str] = None,
    wait: bool = True,
    timeout: float = 900.0,
) -> dict:
    """Submit the Step1 character-sheet workflow for ``name``.

    Performs the live-environment prep before submission:

      1. Calls ``/vnccs/create?name=NAME`` to register the character + write
         its config + create the output directory tree.
      2. Copies VNCCS's bundled CharacterSheetTemplate.png into ComfyUI's
         ``input/`` directory if not already present (workflow's LoadImage
         needs it).
      3. Builds the patched workflow + submits + (optionally) waits.

    Returns ``{prompt_id, client_id, number, node_errors, history?, init?}``.
    """
    if not name:
        raise VnccsError("character name is required")

    # Step 1: REST-init the character so the dropdown contains NAME.
    init_record = init_character_via_rest(name, url=url)

    # Step 2: ensure the bundled pose template is copied into ComfyUI input/.
    comfy = get_comfy_path(comfy_path)
    ensure_input_template(comfy)

    # Step 3: build patched workflow + submit.
    workflow = _build_workflow(name, description, pose=pose, seed=seed)
    result = submit_workflow(workflow, url=url)
    result["init"] = init_record

    if wait and result.get("prompt_id"):
        entry = wait_for_prompt(result["prompt_id"], url=url, timeout=timeout)
        result["history"] = entry

    return result
