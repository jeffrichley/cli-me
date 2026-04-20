"""Shared backend utilities for the VNCCS CLI.

- ComfyUI path / URL resolution (re-uses COMFY_PATH / COMFY_URL conventions
  from the sibling `comfyui` cli-me skill)
- VNCCS custom-node install location discovery (a subdir of COMFY_PATH)
- Bundled workflow JSON loader (our own templates/ dir, version-pinned)
- Typed exception hierarchy with stable exit codes
- Pretty error printer via Rich
"""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from rich.console import Console

DEFAULT_COMFY_URL = "http://127.0.0.1:8188"
VNCCS_CUSTOM_NODE_DIR_NAME = "ComfyUI_VNCCS"
# Subdirectory of ComfyUI's output root where VNCCS persists every
# character's tree. Hard-coded in `utils.base_output_dir()`; see
# references/source-analysis/state-management.md §Root directory.
VNCCS_STATE_SUBDIR = "VN_CharacterCreatorSuit"

# Custom-node packs VNCCS's workflows depend on, by install-directory name.
# Used by `vnccs check nodes` to verify all deps are present.
REQUIRED_CUSTOM_NODE_PACKS = (
    "ComfyUI_VNCCS",
    "ComfyUI-Impact-Pack",
    "ComfyUI-GGUF",
    "ComfyUI-SeedVR2_VideoUpscaler",
    "ComfyUI-Easy-Use",
    "comfyui_controlnet_aux",
    "was-node-suite-comfyui",
    "ComfyUI_UltimateSDUpscale",
    "rgthree-comfy",
)


# Required model files VNCCS 2.1.0 workflows reference.
# Source: references/source-analysis/required-models.md (the 15 explicitly-referenced
# models, plus optional RMBG variants that are auto-downloaded at first use).
#
# `subdir` is relative to `<COMFY_PATH>/models/`. VNCCS workflow JSONs author
# Windows-style backslashes (e.g. `Illustrious\ILFlatMix.safetensors`), but on
# disk the file lives at `models/checkpoints/Illustrious/ILFlatMix.safetensors`.
# We store the filename + subdir already-normalized here so both Windows and
# Linux checks work against Path / forward-slashes.
#
# `optional=True` entries warn-but-don't-fail per playbook.md (RMBG variants).
REQUIRED_MODELS: tuple[dict, ...] = (
    {
        "filename": "qwen-image-edit-2511-Q5_0.gguf",
        "subdir": "unet",
        "type": "UNet (GGUF)",
        "download_url": "https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF",
        "optional": False,
    },
    {
        "filename": "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",
        "subdir": "loras/qwen",
        "type": "LoRA (Qwen Lightning)",
        "download_url": "https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning",
        "optional": False,
    },
    {
        "filename": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "subdir": "clip",
        "type": "CLIP (Qwen 2.5 VL)",
        "download_url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "optional": False,
    },
    {
        "filename": "qwen_image_vae.safetensors",
        "subdir": "vae",
        "type": "VAE (Qwen)",
        "download_url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors",
        "optional": False,
    },
    {
        "filename": "ILFlatMix.safetensors",
        "subdir": "checkpoints/Illustrious",
        "type": "SDXL Checkpoint",
        "download_url": "https://civitai.com (search 'Illustrious ILFlatMix')",
        "optional": False,
    },
    {
        "filename": "mimimeter.safetensors",
        "subdir": "loras/IL",
        "type": "LoRA (SDXL)",
        "download_url": "https://huggingface.co/MIUProject/VNCCS/tree/main",
        "optional": False,
    },
    {
        "filename": "AnytestV4.safetensors",
        "subdir": "controlnet/SDXL",
        "type": "ControlNet (SDXL)",
        "download_url": "https://civitai.com (search 'AnytestV4 ControlNet SDXL')",
        "optional": False,
    },
    {
        "filename": "IllustriousXL_openpose.safetensors",
        "subdir": "controlnet/SDXL",
        "type": "ControlNet (SDXL OpenPose)",
        "download_url": "https://civitai.com (search 'IllustriousXL OpenPose ControlNet')",
        "optional": False,
    },
    {
        "filename": "poser_helper_v2_000004200.safetensors",
        "subdir": "loras/qwen/VNCCS",
        "type": "LoRA (VNCCS Pose Helper)",
        "download_url": "https://huggingface.co/MIUProject/VNCCS/tree/main",
        "optional": False,
    },
    {
        "filename": "ClothesHelperUltimateV1_000005100.safetensors",
        "subdir": "loras/qwen/VNCCS",
        "type": "LoRA (VNCCS Clothes Helper)",
        "download_url": "https://huggingface.co/MIUProject/VNCCS/tree/main",
        "optional": False,
    },
    {
        "filename": "TransferClothes_000006700.safetensors",
        "subdir": "loras/qwen/VNCCS",
        "type": "LoRA (VNCCS Clothes Transfer)",
        "download_url": "https://huggingface.co/MIUProject/VNCCS/tree/main",
        "optional": False,
    },
    {
        "filename": "EmotionCoreV1_000003000.safetensors",
        "subdir": "loras/qwen/VNCCS",
        "type": "LoRA (VNCCS Emotion Core)",
        "download_url": "https://huggingface.co/MIUProject/VNCCS/tree/main",
        "optional": False,
    },
    {
        "filename": "face_yolov8m.pt",
        "subdir": "ultralytics/bbox",
        "type": "YOLO bbox (face)",
        "download_url": "https://huggingface.co/Bingsu/adetailer/blob/main/face_yolov8m.pt",
        "optional": False,
    },
    {
        "filename": "2x_APISR_RRDB_GAN_generator.pth",
        "subdir": "upscale_models",
        "type": "Upscaler (2x APISR)",
        "download_url": "https://github.com/Kiteretsu77/APISR/releases",
        "optional": False,
    },
    {
        "filename": "seedvr2_ema_3b_fp16.safetensors",
        "subdir": "diffusion_models",
        "type": "SeedVR2 DiT",
        "download_url": "https://huggingface.co/numz/SeedVR2_comfyUI",
        "optional": False,
    },
    # Optional RMBG variants — auto-downloaded lazily by the VNCCS_RMBG2 node.
    # Missing these should warn but not fail per playbook.md §check models.
    {
        "filename": "model.safetensors",
        "subdir": "RMBG/RMBG-2.0",
        "type": "RMBG BiRefNet (optional)",
        "download_url": "https://huggingface.co/1038lab/RMBG-2.0",
        "optional": True,
    },
)


# --- Exception hierarchy ---------------------------------------------------


class VnccsError(Exception):
    """Base exception for VNCCS CLI errors."""

    exit_code: int = 1

    def __init__(self, message: str, *, detail: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class VnccsConnectionError(VnccsError):
    """ComfyUI server not reachable."""

    exit_code = 2


class VnccsValidationError(VnccsError):
    """Workflow or command input failed validation before submission."""

    exit_code = 3


class VnccsExecutionError(VnccsError):
    """ComfyUI reported an execution error on the submitted workflow."""

    exit_code = 4


class VnccsNotFoundError(VnccsError):
    """Character / costume / emotion / preset not found on disk."""

    exit_code = 5


class VnccsPathError(VnccsError):
    """COMFY_PATH missing or doesn't look like a ComfyUI install."""

    exit_code = 6


class VnccsWorkflowError(VnccsError):
    """Bundled workflow JSON missing, corrupt, or unparseable."""

    exit_code = 7


# --- Path / URL resolution -------------------------------------------------


def get_comfy_url(cli_url: Optional[str] = None) -> str:
    """Resolve the ComfyUI base URL. --url flag > COMFY_URL env > default."""
    url = cli_url or os.environ.get("COMFY_URL") or DEFAULT_COMFY_URL
    return url.rstrip("/")


def get_comfy_path(cli_path: Optional[str] = None) -> Path:
    """Resolve the ComfyUI install directory.

    Precedence: --path flag > COMFY_PATH env > error. Validates the path
    exists and contains a custom_nodes/ subdirectory.
    """
    raw = cli_path or os.environ.get("COMFY_PATH")
    if not raw:
        raise VnccsPathError(
            "ComfyUI install path not set.",
            detail=(
                "Pass --path /path/to/ComfyUI, or set the COMFY_PATH env var. "
                "This should be the directory that contains custom_nodes/, models/, main.py."
            ),
        )
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise VnccsPathError(
            f"ComfyUI path does not exist: {path}",
            detail=f"Resolved from {'--path' if cli_path else 'COMFY_PATH'}={raw!r}.",
        )
    if not (path / "custom_nodes").is_dir():
        raise VnccsPathError(
            f"Path is not a ComfyUI install: {path}",
            detail=f"Expected {path / 'custom_nodes'} to be a directory.",
        )
    return path


def get_vnccs_install_dir(comfy_path: Optional[str] = None) -> Path:
    """Return the ComfyUI_VNCCS custom-node install directory.

    Raises VnccsPathError if ComfyUI's custom_nodes/ doesn't contain VNCCS.
    """
    comfy = get_comfy_path(comfy_path)
    vnccs = comfy / "custom_nodes" / VNCCS_CUSTOM_NODE_DIR_NAME
    if not vnccs.is_dir():
        raise VnccsPathError(
            f"ComfyUI_VNCCS not installed at {vnccs}",
            detail=(
                "Install it via the sibling comfyui skill:\n"
                "  comfyui custom-nodes install https://github.com/AHEKOT/ComfyUI_VNCCS.git"
            ),
        )
    return vnccs


def get_vnccs_state_dir(
    comfy_path: Optional[str] = None,
    *,
    state_dir: Optional[str] = None,
) -> Path:
    """Return the root directory where VNCCS persists per-character state.

    Resolution precedence:
      1. Explicit `state_dir` argument (from a `--state-dir` flag).
      2. `VNCCS_STATE_DIR` env var (lets users override when ComfyUI was
         launched with `--output-directory` pointing elsewhere).
      3. Default `<COMFY_PATH>/output/VN_CharacterCreatorSuit`.

    The directory is NOT required to exist — missing-dir is a normal
    "no characters have been created yet" state. The caller decides
    whether to treat a non-existent root as empty or as an error.
    """
    if state_dir:
        return Path(state_dir).expanduser().resolve()
    env_override = os.environ.get("VNCCS_STATE_DIR")
    if env_override:
        return Path(env_override).expanduser().resolve()
    comfy = get_comfy_path(comfy_path)
    return (comfy / "output" / VNCCS_STATE_SUBDIR).resolve()


# --- Bundled workflow loading ----------------------------------------------


def bundled_workflow_path(name: str) -> Path:
    """Return the path to a bundled VNCCS workflow JSON (e.g. 'VN_Step1_...v1.json').

    Bundled workflows live in scripts/workflows/ pinned to a specific VNCCS
    version (see scripts/workflows/README.md for version + sha256).
    """
    here = Path(__file__).resolve().parent.parent
    return here / "workflows" / name


def load_bundled_workflow(name: str) -> dict:
    """Load and parse a bundled workflow JSON. Raises VnccsWorkflowError on failure."""
    path = bundled_workflow_path(name)
    if not path.exists():
        raise VnccsWorkflowError(
            f"Bundled workflow missing: {name}",
            detail=(
                f"Expected at {path}. It ships with the skill; re-install "
                "the comfyui-vnccs skill to restore the workflow bundle."
            ),
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise VnccsWorkflowError(
            f"Bundled workflow is not valid JSON: {name}",
            detail=f"{path}: {e}",
        ) from e


# --- Pretty error printing -------------------------------------------------


_stderr = Console(stderr=True)


def print_error_and_exit(err: VnccsError) -> None:
    """Print a VnccsError to stderr via Rich and exit with its exit_code."""
    _stderr.print(f"[bold red]error:[/bold red] {err.message}")
    if err.detail:
        _stderr.print(f"[dim]{err.detail}[/dim]")
    sys.exit(err.exit_code)
