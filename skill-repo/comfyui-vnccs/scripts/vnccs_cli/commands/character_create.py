"""Logic for `vnccs character create` — stage 1 character sheet generation.

Submits the bundled **V1SDXL legacy** character-sheet workflow (stable
path). Patches the ``CharacterCreator`` node with the user-supplied name
+ description, optional pose preset, optional explicit seed.

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

    if pose:
        # Pose preset filename is referenced by the LoadImage titled
        # "Character sheet" in the workflow. VNCCS bundles PNGs in
        # <VNCCS>/presets/poses/ and the LoadImage input wants the filename.
        pose_patched = patch_workflow_node(
            workflow,
            class_type="LoadImage",
            title="Character sheet",
            inputs={"image": f"{pose}.png"},
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
    return workflow


def run_create(
    name: str,
    description: str,
    *,
    pose: Optional[str] = None,
    seed: Optional[int] = None,
    url: Optional[str] = None,
    wait: bool = True,
    timeout: float = 600.0,
) -> dict:
    """Submit the Step1 character-sheet workflow for ``name``.

    Returns ``{prompt_id, client_id, number, node_errors, history?}``.
    ``history`` is populated only when ``wait=True``.
    """
    if not name:
        raise VnccsError("character name is required")

    workflow = _build_workflow(name, description, pose=pose, seed=seed)

    result = submit_workflow(workflow, url=url)

    if wait and result.get("prompt_id"):
        entry = wait_for_prompt(result["prompt_id"], url=url, timeout=timeout)
        result = dict(result)
        result["history"] = entry

    return result
