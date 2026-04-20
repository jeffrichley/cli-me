"""Logic for `vnccs emotion add` — stage 3 emotion sheet generation.

Default path (``--legacy``, the default) submits the V1SDXL
``EmotionGeneratorV2`` workflow. The ``--qwen`` path refuses immediately
with exit 4 because VNCCS 2.1.0's QWEN emotion workflow references two
node classes (``VNCCS_QWEN_Detailer`` / ``VNCCS_BBox_Extractor``) that
are unregistered in any published VNCCS branch — documented in
``references/gotchas.md`` and ``scripts/workflows/README.md``.

Switch to ``--qwen`` after upstream ships the missing classes.
"""

from __future__ import annotations

import json as _json
from typing import Any, Optional

from vnccs_cli.backend import (
    VnccsError,
    VnccsExecutionError,
    VnccsNotFoundError,
    VnccsValidationError,
    VnccsWorkflowError,
    get_vnccs_state_dir,
    load_api_workflow,
    patch_workflow_node,
    submit_workflow,
    wait_for_prompt,
)

STEP3_LEGACY_WORKFLOW = "V1SDXL/VN_Step3_CharEmotionGeneratorV6_api.json"
STEP3_QWEN_WORKFLOW = "VN_Step3_QWEN_EmotionStudio_V1_api.json"  # broken upstream


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


def _build_legacy_workflow(
    character: str,
    emotion: str,
    costume: str,
) -> dict:
    workflow = load_api_workflow(STEP3_LEGACY_WORKFLOW)

    inputs: dict[str, Any] = {
        "character": character,
        # EmotionGeneratorV2 wants JSON-encoded arrays — see the bundled
        # workflow's defaults, e.g. '["Naked"]' / '["cat-smile-nyan"]'.
        "costumes_data": _json.dumps([costume]),
        "emotions_data": _json.dumps([emotion]),
        "prompt_style": "SDXL Style",
    }
    patched = patch_workflow_node(
        workflow, class_type="EmotionGeneratorV2", inputs=inputs
    )
    if patched == 0:
        raise VnccsWorkflowError(
            "EmotionGeneratorV2 node missing from Step3 legacy workflow.",
            detail=(
                f"Bundled workflow {STEP3_LEGACY_WORKFLOW} appears corrupt — "
                "re-install the comfyui-vnccs skill."
            ),
        )
    return workflow


def run_add(
    character: str,
    emotion: str,
    *,
    costume: str = "Naked",
    legacy: bool = True,
    qwen: bool = False,
    denoise: Optional[float] = None,  # noqa: ARG001 — reserved for QWEN path
    seed: Optional[int] = None,  # noqa: ARG001 — reserved for QWEN path
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
    url: Optional[str] = None,
    wait: bool = True,
    timeout: float = 600.0,
) -> dict:
    """Submit Step3 emotion workflow. Default --legacy (SDXL), --qwen refused.

    Returns ``{prompt_id, client_id, number, node_errors, history?}``.
    Raises ``VnccsValidationError`` (exit 3) if both flags set, or
    ``VnccsExecutionError`` (exit 4) on --qwen (upstream broken).
    """
    if not character:
        raise VnccsError("character is required")
    if not emotion:
        raise VnccsError("--emotion is required")

    if legacy and qwen:
        raise VnccsValidationError(
            "--legacy and --qwen are mutually exclusive"
        )
    # Default is legacy; --qwen explicitly opts into the broken path.
    use_qwen = qwen and not legacy

    if use_qwen:
        raise VnccsExecutionError(
            "--qwen emotion workflow is broken upstream.",
            detail=(
                "VNCCS 2.1.0's QWEN emotion workflow references "
                "VNCCS_QWEN_Detailer and VNCCS_BBox_Extractor, which are "
                "not registered in any published VNCCS branch. Use the "
                "default --legacy (SDXL) path until upstream ships the "
                "missing node classes. See references/gotchas.md."
            ),
        )

    _assert_character_exists(
        character, comfy_path=comfy_path, state_dir=state_dir
    )

    workflow = _build_legacy_workflow(character, emotion, costume)
    result = submit_workflow(workflow, url=url)

    if wait and result.get("prompt_id"):
        entry = wait_for_prompt(result["prompt_id"], url=url, timeout=timeout)
        result = dict(result)
        result["history"] = entry
    return result
