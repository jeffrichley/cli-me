"""Logic for `vnccs sprite render` — stage 4 final-sprite rendering.

Submits Step4 ``SpriteGenerator`` with ``character=<name>``. Per the
VNCCS sprite_generator node design there's no per-costume filter — the
single workflow renders every ``(costume × emotion)`` combination the
character has on disk. Slow: minutes per character on GPU.
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

STEP4_WORKFLOW = "VN_Step4_CharSpriteCreatorV5_api.json"


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
            detail=f"Expected directory {char_dir}.",
        )


def _build_workflow(character: str) -> dict:
    workflow = load_api_workflow(STEP4_WORKFLOW)

    inputs: dict[str, Any] = {"character": character}
    patched = patch_workflow_node(
        workflow, class_type="SpriteGenerator", inputs=inputs
    )
    if patched == 0:
        raise VnccsWorkflowError(
            "SpriteGenerator node missing from Step4 workflow.",
            detail=(
                f"Bundled workflow {STEP4_WORKFLOW} appears corrupt — "
                "re-install the comfyui-vnccs skill."
            ),
        )
    return workflow


def run_render(
    character: str,
    *,
    seed: Optional[int] = None,  # noqa: ARG001 — SpriteGenerator has no seed widget
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
    url: Optional[str] = None,
    wait: bool = True,
    timeout: float = 900.0,
) -> dict:
    """Submit Step4 sprite-render workflow for ``character``.

    ``seed`` is accepted for future-compat but the bundled SpriteGenerator
    node has no seed widget — sprite composition is deterministic given
    the on-disk costume + emotion sheets. A future VNCCS release may
    expose per-run variation.
    """
    if not character:
        raise VnccsError("character is required")

    _assert_character_exists(
        character, comfy_path=comfy_path, state_dir=state_dir
    )

    workflow = _build_workflow(character)
    result = submit_workflow(workflow, url=url)

    if wait and result.get("prompt_id"):
        entry = wait_for_prompt(result["prompt_id"], url=url, timeout=timeout)
        result = dict(result)
        result["history"] = entry
    return result
