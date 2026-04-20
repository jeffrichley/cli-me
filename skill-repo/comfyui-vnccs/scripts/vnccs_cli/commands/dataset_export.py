"""Logic for `vnccs dataset export` — stage 5 LoRA dataset packaging.

Submits Step5 ``DatasetGenerator`` with ``character=<name>`` and
``game_name=<game>``. After successful completion ComfyUI has written
the dataset into VNCCS's per-character ``lora/`` subdirectory; we copy
that directory to ``--out``.

If ``--out`` is not provided we still run the workflow (so VNCCS
produces the on-disk dataset in its default location) and return the
VNCCS-internal path for downstream tooling.
"""

from __future__ import annotations

import shutil
from pathlib import Path
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

STEP5_WORKFLOW = "VN_Step5_LoraDataSetGeneratorV5_api.json"
DEFAULT_GAME_NAME = "VN"


def _assert_character_exists(
    character: str,
    *,
    comfy_path: Optional[str],
    state_dir: Optional[str],
) -> Path:
    root = get_vnccs_state_dir(comfy_path, state_dir=state_dir)
    char_dir = root / character
    if not char_dir.is_dir():
        raise VnccsNotFoundError(
            f"Character not found: {character}",
            detail=f"Expected directory {char_dir}.",
        )
    return char_dir


def _build_workflow(character: str, game_name: str) -> dict:
    workflow = load_api_workflow(STEP5_WORKFLOW)

    inputs: dict[str, Any] = {
        "character": character,
        "game_name": game_name,
    }
    patched = patch_workflow_node(
        workflow, class_type="DatasetGenerator", inputs=inputs
    )
    if patched == 0:
        raise VnccsWorkflowError(
            "DatasetGenerator node missing from Step5 workflow.",
            detail=(
                f"Bundled workflow {STEP5_WORKFLOW} appears corrupt — "
                "re-install the comfyui-vnccs skill."
            ),
        )
    return workflow


def _copy_lora_dir(src: Path, dst: Path) -> dict:
    """Copy VNCCS's <character>/lora/ tree to ``dst``. Returns file counts."""
    if not src.is_dir():
        raise VnccsNotFoundError(
            f"VNCCS did not produce a lora/ directory for this character: {src}",
            detail=(
                "Dataset generation ran to completion but the expected "
                f"{src} is missing. Check ComfyUI logs for stage-5 errors."
            ),
        )
    dst.mkdir(parents=True, exist_ok=True)

    png_count = 0
    txt_count = 0
    for item in src.rglob("*"):
        if item.is_file():
            rel = item.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            suffix = item.suffix.lower()
            if suffix == ".png":
                png_count += 1
            elif suffix == ".txt":
                txt_count += 1
    return {"png_count": png_count, "txt_count": txt_count}


def run_export(
    character: str,
    *,
    out: Optional[str] = None,
    game_name: Optional[str] = None,
    comfy_path: Optional[str] = None,
    state_dir: Optional[str] = None,
    url: Optional[str] = None,
    wait: bool = True,
    timeout: float = 900.0,
) -> dict:
    """Submit Step5; on success copy VNCCS's ``lora/`` tree to ``out``.

    Returns a dict summarizing the submission plus (when ``out`` was
    provided and the copy ran) the post-copy file counts.
    """
    if not character:
        raise VnccsError("character is required")

    char_dir = _assert_character_exists(
        character, comfy_path=comfy_path, state_dir=state_dir
    )
    resolved_game = game_name or DEFAULT_GAME_NAME

    workflow = _build_workflow(character, resolved_game)
    result = submit_workflow(workflow, url=url)

    payload: dict[str, Any] = {
        "character": character,
        "game_name": resolved_game,
        "submission": result,
        "vnccs_lora_dir": str(char_dir / "lora"),
    }

    if wait and result.get("prompt_id"):
        entry = wait_for_prompt(result["prompt_id"], url=url, timeout=timeout)
        payload["submission"] = dict(result)
        payload["submission"]["history"] = entry

        if out:
            lora_src = char_dir / "lora"
            lora_dst = Path(out).expanduser().resolve()
            copy_stats = _copy_lora_dir(lora_src, lora_dst)
            payload["out"] = str(lora_dst)
            payload["copy_stats"] = copy_stats

    return payload
