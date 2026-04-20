"""Logic for `vnccs character clone` — stage 1.1 derive-from-existing.

Submits the bundled Step1.1 QWEN clone workflow. QWEN is intentional
here (not the V1SDXL legacy) because reference-image cloning is QWEN's
strength and Step1.1 does NOT depend on the broken Step3 nodes. Patches
the ``CharacterCreator`` node with ``existing_character=<from>`` and
``new_character_name=<name>``; optional ``prompt`` routes to
``additional_details``; optional ``seed`` overrides the widget.
"""

from __future__ import annotations

from typing import Any, Optional

from vnccs_cli.backend import (
    VnccsError,
    VnccsNotFoundError,
    VnccsWorkflowError,
    get_vnccs_state_dir,
    load_api_workflow,
    patch_workflow_node,
    submit_workflow,
    wait_for_prompt,
)

STEP1_1_CLONE_WORKFLOW = "VN_Step1.1_QWEN_Clone_Existing_Character_v1_api.json"


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
    prompt: Optional[str] = None,
    seed: Optional[int] = None,
) -> dict:
    workflow = load_api_workflow(STEP1_1_CLONE_WORKFLOW)

    inputs: dict[str, Any] = {
        "new_character_name": name,
        "existing_character": source,
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
    return workflow


def run_clone(
    name: str,
    source: str,
    *,
    prompt: Optional[str] = None,
    seed: Optional[int] = None,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
    url: Optional[str] = None,
    wait: bool = True,
    timeout: float = 600.0,
) -> dict:
    """Submit the Step1.1 clone workflow deriving ``name`` from ``source``.

    Returns ``{prompt_id, client_id, number, node_errors, history?}``.
    """
    if not name:
        raise VnccsError("character name is required")
    if not source:
        raise VnccsError("--from source character is required")

    _assert_source_exists(source, comfy_path=comfy_path, state_dir=state_dir)

    workflow = _build_workflow(name, source, prompt=prompt, seed=seed)
    result = submit_workflow(workflow, url=url)

    if wait and result.get("prompt_id"):
        entry = wait_for_prompt(result["prompt_id"], url=url, timeout=timeout)
        result = dict(result)
        result["history"] = entry
    return result
