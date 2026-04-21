"""Logic for `vnccs character clone` — stage 1.1 derive-from-existing.

Submits the bundled Step1.1 QWEN clone workflow. QWEN is intentional
here (not the V1SDXL legacy) because reference-image cloning is QWEN's
strength and Step1.1 does NOT depend on the broken Step3 nodes.

Live-env prep (same shape as character_create):
  - ``/vnccs/create?name=<new_name>`` REST init so the target appears in
    CharacterCreator's existing_character dropdown before submission.
  - Reference image: workflow defaults to a stale author-local filename;
    we auto-copy the source character's ``sheet_neutral_00001_.png`` into
    ComfyUI's input/ as ``clone_ref_<source>.png`` and patch the LoadImage
    to use it. Users can override with ``--ref-image FILENAME`` (must be
    an existing file in ComfyUI's input/ directory).
  - VNCCS_RMBG2 ``background='Green'`` (same as clothing_add).
  - Prune orphaned PreviewImage nodes.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional

from vnccs_cli.backend import (
    VnccsError,
    VnccsNotFoundError,
    VnccsPathError,
    VnccsWorkflowError,
    get_comfy_path,
    get_vnccs_state_dir,
    init_character_via_rest,
    load_api_workflow,
    patch_workflow_node,
    prune_orphaned_output_nodes,
    submit_workflow,
    wait_for_prompt,
)

STEP1_1_CLONE_WORKFLOW = "VN_Step1.1_QWEN_Clone_Existing_Character_v1_api.json"


def _copy_source_sheet_to_input(
    source: str,
    *,
    comfy_path: Path,
    state_dir: Path,
) -> str:
    """Copy the source character's neutral sheet into ComfyUI's input/.

    Returns the basename used (which the workflow's LoadImage will
    reference). Raises VnccsNotFoundError if the source character has
    no sheet_neutral_*.png yet (user hasn't finished Step1).
    """
    src_sheet_dir = state_dir / source / "Sheets" / "Naked" / "neutral"
    if not src_sheet_dir.is_dir():
        raise VnccsNotFoundError(
            f"Source character has no neutral sheet dir: {src_sheet_dir}",
            detail=(
                f"Run `vnccs character create {source} ...` first — clone "
                "needs a completed stage-1 sheet as the reference image."
            ),
        )
    candidates = sorted(src_sheet_dir.glob("sheet_neutral_*.png"))
    if not candidates:
        raise VnccsNotFoundError(
            f"Source character has no sheet_neutral PNGs: {src_sheet_dir}",
            detail=(
                f"Expected at least one sheet_neutral_NNNNN_.png under "
                f"{src_sheet_dir}."
            ),
        )
    src_sheet = candidates[-1]  # newest (highest NNNNN)
    dst_name = f"clone_ref_{source}.png"
    dst = comfy_path / "input" / dst_name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_sheet, dst)
    return dst_name


def _assert_source_exists(
    source: str,
    *,
    comfy_path: Optional[str],
    state_dir: Optional[str],
) -> None:
    """Fail fast with exit 5 if the source character's state dir is missing."""
    root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)
    char_dir = root / source
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Source character not found: {source}",
            detail=(
                f"Expected directory {char_dir}. List existing characters with "
                "`vnccs character list`."
            ),
        )


def _build_workflow(
    name: str,
    source: str,
    *,
    ref_image: str,
    prompt: Optional[str] = None,
    seed: Optional[int] = None,
) -> dict:
    workflow = load_api_workflow(STEP1_1_CLONE_WORKFLOW)

    # After REST init, the new name is in the dropdown — address it.
    inputs: dict[str, Any] = {
        "new_character_name": name,
        "existing_character": name,
    }
    if prompt is not None:
        inputs["additional_details"] = prompt
    if seed is not None:
        inputs["seed"] = int(seed)

    patched = patch_workflow_node(
        workflow, class_type="CharacterCreator", inputs=inputs
    )
    if patched == 0:
        raise VnccsWorkflowError(
            "CharacterCreator node missing from Step1.1 clone workflow.",
            detail=(
                f"Bundled workflow {STEP1_1_CLONE_WORKFLOW} appears corrupt — "
                "re-install the comfyui-vnccs skill."
            ),
        )

    # Reference image: point LoadImage at the source character's sheet
    # (or user-specified filename, already copied into ComfyUI/input/).
    patch_workflow_node(
        workflow, class_type="LoadImage", inputs={"image": ref_image}
    )

    # VNCCS_RMBG2 default 'Color' -> 'Green' (live-env prep).
    patch_workflow_node(
        workflow, class_type="VNCCS_RMBG2", inputs={"background": "Green"}
    )
    prune_orphaned_output_nodes(workflow)
    return workflow


def run_clone(
    name: str,
    source: str,
    *,
    prompt: Optional[str] = None,
    seed: Optional[int] = None,
    ref_image: Optional[str] = None,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
    url: Optional[str] = None,
    wait: bool = True,
    timeout: float = 900.0,
) -> dict:
    """Submit the Step1.1 clone workflow deriving ``name`` from ``source``.

    Performs live-env prep: REST-initializes the NEW character via
    /vnccs/create, copies source's neutral sheet into ComfyUI/input/
    as the reference image (unless ``ref_image`` overrides), patches
    LoadImage + RMBG2 + prunes orphan previews before submit.

    Returns ``{prompt_id, client_id, number, node_errors, history?, init?}``.
    """
    if not name:
        raise VnccsError("character name is required")
    if not source:
        raise VnccsError("--from source character is required")

    _assert_source_exists(source, comfy_path=comfy_path, state_dir=state_dir)

    comfy = get_comfy_path(comfy_path)
    state_root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)

    # Reference image: either the user's override (must already exist in
    # ComfyUI/input/) or auto-copy the source's newest neutral sheet.
    if ref_image:
        if not (comfy / "input" / ref_image).is_file():
            raise VnccsPathError(
                f"--ref-image {ref_image!r} not found in ComfyUI/input/",
                detail=(
                    f"Place the file at {comfy / 'input' / ref_image} "
                    "before running clone."
                ),
            )
        resolved_ref = ref_image
    else:
        resolved_ref = _copy_source_sheet_to_input(
            source, comfy_path=comfy, state_dir=state_root
        )

    # REST-init the new character so the dropdown includes the name.
    init_record = init_character_via_rest(name, url=url)

    workflow = _build_workflow(
        name, source, ref_image=resolved_ref, prompt=prompt, seed=seed
    )
    result = submit_workflow(workflow, url=url)
    result["init"] = init_record
    result["ref_image"] = resolved_ref

    if wait and result.get("prompt_id"):
        entry = wait_for_prompt(result["prompt_id"], url=url, timeout=timeout)
        result = dict(result)
        result["history"] = entry
    return result
