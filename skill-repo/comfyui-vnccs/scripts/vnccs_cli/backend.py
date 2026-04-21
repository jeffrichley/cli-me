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
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import httpx
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
    "ComfyUI-Impact-Subpack",
    "ComfyUI-KJNodes",
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
    {
        "filename": "ema_vae_fp16.safetensors",
        "subdir": "diffusion_models",
        "type": "SeedVR2 VAE",
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
    # --- Found by inspecting bundled API workflows (post-init audit) ---
    # Reference: tmp/inspect_workflow_models.py walked every Loader-class
    # node across all 9 bundled API workflows and surfaced these literal
    # filenames — they were missing from the original required-models list
    # but the workflows fail without them.
    {
        "filename": "dmd2_sdxl_4step_lora_fp16.safetensors",
        "subdir": "loras/DMD2",
        "type": "LoRA (DMD2 4-step Lightning)",
        "download_url": "https://huggingface.co/MIUProject/VNCCS/tree/main",
        "optional": False,
    },
    {
        "filename": "vn_character_sheet_v4.safetensors",
        "subdir": "loras",
        "type": "LoRA (VN Character Sheet v4)",
        "download_url": "https://huggingface.co/MIUProject/VNCCS/tree/main",
        "optional": False,
    },
    {
        "filename": "4x_APISR_GRL_GAN_generator.pth",
        "subdir": "upscale_models",
        "type": "Upscaler (4x APISR GRL)",
        "download_url": "https://huggingface.co/MIUProject/VNCCS/tree/main",
        "optional": False,
    },
    {
        "filename": "sam_vit_b_01ec64.pth",
        "subdir": "sams",
        "type": "SAM (ViT-B)",
        "download_url": "https://huggingface.co/MIUProject/VNCCS/tree/main",
        "optional": False,
    },
    {
        "filename": "face_yolov8m-seg_60.pt",
        "subdir": "ultralytics/segm",
        "type": "YOLO segmentation (face)",
        "download_url": "https://huggingface.co/Bingsu/adetailer/blob/main/face_yolov8m-seg_60.pt",
        "optional": False,
    },
    # Illustrious checkpoint — VNCCS workflows hard-code a specific filename
    # but the README says "any illustrious based model" works. We pin both
    # filenames the bundled workflows reference; substitute with WAI-illustrious
    # from civitai or any compatible Illustrious SDXL checkpoint, saved under
    # these names. See gotchas.md §illustrious-checkpoint-substitution.
    {
        "filename": "ILFlatMixV4_00001_.safetensors",
        "subdir": "checkpoints/Illustrious",
        "type": "SDXL Checkpoint (V1SDXL workflows)",
        "download_url": (
            "civitai (substitute any Illustrious SDXL checkpoint, "
            "e.g. https://civitai.com/models/827184/wai-illustrious-sdxl)"
        ),
        "optional": False,
    },
    {
        "filename": "ILFlatMix.safetensors",
        "subdir": "checkpoints/Illustrious",
        "type": "SDXL Checkpoint (QWEN workflows)",
        "download_url": (
            "civitai (substitute any Illustrious SDXL checkpoint, "
            "e.g. https://civitai.com/models/827184/wai-illustrious-sdxl)"
        ),
        "optional": False,
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


# --- ComfyUI extra_model_paths.yaml -----------------------------------------


def parse_extra_model_paths(comfy_path: Path) -> list[tuple[str, Path]]:
    """Parse ``<comfy_path>/extra_model_paths.yaml`` if present.

    Returns a list of ``(model_type, dir)`` pairs — one per search location.
    ComfyUI lets users redirect model directories via this YAML; without
    parsing it the wrapper would falsely report installed models as missing
    (real bug seen in the field where models live at ``E:/data/comfy/models/``
    rather than under the ComfyUI install).

    Format (subset we support):
    ::
        section_name:
            base_path: /absolute/path/
            checkpoints: checkpoints/
            loras: loras/
            text_encoders: |
                text_encoders/
                clip/

    Each non-``base_path`` non-``is_default`` key under each section is a
    ComfyUI model type (``checkpoints``, ``loras``, ``unet``, ``vae``, …);
    its value is one or more whitespace-separated relative subdirs. Multiple
    sections are allowed (e.g. one per ComfyUI/A1111 install).

    Returns ``[]`` on missing file, parse failure, or YAML lib not installed
    — the caller degrades to the default ``<COMFY_PATH>/models/`` location.
    """
    yaml_file = comfy_path / "extra_model_paths.yaml"
    if not yaml_file.is_file():
        return []
    try:
        import yaml  # PyYAML; optional dep — fall back silently if missing
    except ImportError:
        return []
    try:
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(data, dict):
        return []

    result: list[tuple[str, Path]] = []
    for section in data.values():
        if not isinstance(section, dict):
            continue
        base_raw = section.get("base_path")
        if not base_raw or not isinstance(base_raw, str):
            continue
        base = Path(base_raw).expanduser()
        for key, value in section.items():
            if key in ("base_path", "is_default"):
                continue
            if not isinstance(value, str):
                continue
            for line in value.split():
                stripped = line.strip().rstrip("/").rstrip("\\")
                if stripped:
                    result.append((key, base / stripped))
    return result


def parse_default_base_paths(comfy_path: Path) -> list[Path]:
    """Return ``base_path`` directories from sections marked ``is_default: true``.

    ComfyUI treats ``is_default: true`` sections as fall-back search roots
    for ANY model type (even ones not explicitly listed in the section).
    Without honoring this, a config like the user's — which redirects
    ``checkpoints``/``loras``/etc. to ``E:/data/comfy/models/`` and lets
    ``ultralytics``/``sams`` fall through implicitly — will falsely report
    those files as missing.
    """
    yaml_file = comfy_path / "extra_model_paths.yaml"
    if not yaml_file.is_file():
        return []
    try:
        import yaml
    except ImportError:
        return []
    try:
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(data, dict):
        return []
    bases: list[Path] = []
    for section in data.values():
        if not isinstance(section, dict):
            continue
        if not section.get("is_default"):
            continue
        base_raw = section.get("base_path")
        if isinstance(base_raw, str):
            bases.append(Path(base_raw).expanduser())
    return bases


def find_model_path(
    comfy_path: Path, subdir: str, filename: str
) -> tuple[Path, bool]:
    """Locate a model file across the canonical + extra_model_paths dirs.

    ``subdir`` is the model's path relative to ``models/`` as recorded in
    ``REQUIRED_MODELS`` (e.g. ``"checkpoints/Illustrious"``,
    ``"loras/qwen/VNCCS"``). Splits on the first component to find the
    ComfyUI model type and treats the rest as a subtree under each
    candidate root.

    Search order:
      1. ``<COMFY_PATH>/models/<subdir>/<filename>`` (canonical)
      2. Every explicit ``<type>: <dir>`` entry from extra_model_paths.yaml
         that matches the leading component of ``subdir``.
      3. Every ``base_path`` from ``is_default: true`` sections, joined with
         the full ``subdir`` (catches model types that aren't explicitly
         redirected — the YAML's fall-through behavior).

    Returns ``(path, present)``. ``path`` is the first matching real file,
    or — if missing everywhere — the default canonical location (so error
    messages point to the spot a fresh install would expect).
    A 0-byte file is treated as missing (partial-download guard).
    """
    default = comfy_path / "models" / subdir / filename

    parts = Path(subdir).parts
    if not parts:
        try:
            return default, default.is_file() and default.stat().st_size > 0
        except OSError:
            return default, False

    model_type = parts[0]
    subtree = Path(*parts[1:]) if len(parts) > 1 else None

    candidates: list[Path] = [default]
    for type_name, type_dir in parse_extra_model_paths(comfy_path):
        if type_name != model_type:
            continue
        candidate = type_dir / subtree if subtree else type_dir
        candidates.append(candidate / filename)

    # Fall-through: is_default sections apply to ANY model type.
    for base in parse_default_base_paths(comfy_path):
        candidates.append(base / subdir / filename)

    for c in candidates:
        try:
            if c.is_file() and c.stat().st_size > 0:
                return c, True
        except OSError:
            continue
    return default, False


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


def _api_workflow_path(name: str) -> Path:
    """Resolve a bundled API-format workflow file. Hookable by tests."""
    here = Path(__file__).resolve().parent.parent
    return here / "workflows" / "api" / name


def load_api_workflow(name: str) -> dict:
    """Load a bundled API-format workflow JSON from scripts/workflows/api/<name>.

    `name` may contain a subdirectory prefix (e.g. ``V1SDXL/VN_Step3_...json``).
    Raises VnccsWorkflowError (exit 7) if the file is missing or unparseable.
    """
    path = _api_workflow_path(name)
    if not path.exists():
        raise VnccsWorkflowError(
            f"Bundled API workflow missing: {name}",
            detail=(
                f"Expected at {path}. It ships with the skill; re-install "
                "the comfyui-vnccs skill to restore the workflow bundle."
            ),
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise VnccsWorkflowError(
            f"Bundled API workflow is not valid JSON: {name}",
            detail=f"{path}: {e}",
        ) from e


# --- Workflow patching -----------------------------------------------------


def prune_orphaned_output_nodes(workflow: dict) -> list[str]:
    """Remove PreviewImage/SaveImage nodes with missing or None images input.

    Bundled VNCCS workflows carry debug-only PreviewImage / SaveImage
    nodes that the upstream author left unwired. ComfyUI's validator
    rejects the whole prompt with ``required_input_missing`` when it
    sees one. Safe to delete: these nodes only emit UI previews and
    have no downstream consumers.

    Matches two forms of orphanhood:
      1. ``inputs`` dict is empty / missing ``images`` key entirely
         (e.g. ``{"inputs": {}}``).
      2. ``inputs["images"]`` is literally None.

    Returns the list of node IDs that were removed.
    """
    removed: list[str] = []
    OUTPUT_TYPES = {"PreviewImage", "SaveImage"}
    to_delete: list[str] = []
    for nid, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") not in OUTPUT_TYPES:
            continue
        node_inputs = node.get("inputs") or {}
        images = node_inputs.get("images", "__missing__")
        if images == "__missing__" or images is None:
            to_delete.append(nid)
    for nid in to_delete:
        del workflow[nid]
        removed.append(nid)
    return removed


def patch_workflow_node(
    workflow: dict,
    *,
    class_type: Optional[str] = None,
    title: Optional[str] = None,
    inputs: Optional[dict[str, Any]] = None,
) -> int:
    """Patch matching nodes' ``inputs`` dict in-place. Returns count patched.

    A node matches when its ``class_type`` equals ``class_type`` (if given)
    AND its ``_meta.title`` equals ``title`` (if given). At least one
    selector must be provided. Missing input keys are added; existing keys
    are overwritten. Non-dict top-level values (``_version``, arrays, etc.)
    are ignored.
    """
    if class_type is None and title is None:
        raise ValueError(
            "patch_workflow_node requires at least one of class_type or title."
        )
    if not inputs:
        return 0
    count = 0
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        if class_type is not None and node.get("class_type") != class_type:
            continue
        if title is not None:
            meta = node.get("_meta") or {}
            if meta.get("title") != title:
                continue
        node_inputs = node.setdefault("inputs", {})
        node_inputs.update(inputs)
        count += 1
    return count


# --- Live-environment prep --------------------------------------------------


CHARACTER_SHEET_TEMPLATE = "CharacterSheetTemplate.png"


def ensure_input_template(comfy_path: Path) -> Path:
    """Copy VNCCS's bundled CharacterSheetTemplate.png into ComfyUI's input/.

    The bundled API workflow's LoadImage titled "Character sheet" expects
    this template at runtime — without it, ComfyUI's input validation
    rejects the workflow. The template ships with VNCCS at
    ``<vnccs>/character_template/CharacterSheetTemplate.png`` but isn't
    auto-installed into ``<comfy>/input/``. This helper copies it once.

    Returns the destination path. No-op if the file is already present.
    """
    src = (
        comfy_path
        / "custom_nodes"
        / VNCCS_CUSTOM_NODE_DIR_NAME
        / "character_template"
        / CHARACTER_SHEET_TEMPLATE
    )
    dst = comfy_path / "input" / CHARACTER_SHEET_TEMPLATE
    if dst.exists() and dst.stat().st_size > 0:
        return dst
    if not src.is_file():
        raise VnccsPathError(
            f"VNCCS character template missing: {src}",
            detail=(
                "Expected the bundled CharacterSheetTemplate.png in VNCCS's "
                "character_template/ directory. Re-install VNCCS or check "
                "that the custom-node dir is intact."
            ),
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(src, dst)
    return dst


def init_costume_via_rest(
    character: str,
    costume: str,
    *,
    url: Optional[str] = None,
    timeout: float = 60.0,
) -> dict:
    """Initialize a VNCCS costume via ``/vnccs/create_costume`` REST endpoint.

    Without this call, the CharacterAssetSelector's ``costume`` dropdown
    doesn't include the new costume name — so even with
    ``new_costume_name=COSTUME`` patched into the node, VNCCS writes
    outputs to whatever the dropdown actually points to (usually ``Naked``).
    The endpoint writes the config entry + creates
    ``Sheets/<costume>/neutral/`` on disk.

    Idempotent: returns the existing costume error as a 200-but-warning
    style body if the name already exists (we don't raise in that case
    because re-running clothing add should be safe).

    Returns the parsed JSON dict.
    """
    if not character:
        raise VnccsError("character is required for costume init")
    if not costume:
        raise VnccsError("costume is required for costume init")
    base = get_comfy_url(url)
    try:
        with httpx.Client(base_url=base, timeout=timeout) as client:
            response = client.get(
                "/vnccs/create_costume",
                params={"character": character, "costume": costume},
            )
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
    ) as exc:
        raise VnccsConnectionError(
            f"Cannot reach ComfyUI at {base}",
            detail=str(exc),
        ) from exc
    if response.status_code >= 400:
        raise VnccsExecutionError(
            f"VNCCS /vnccs/create_costume failed (HTTP {response.status_code}).",
            detail=response.text[:1000],
        )
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise VnccsExecutionError(
            "VNCCS /vnccs/create_costume returned non-JSON.",
            detail=str(exc),
        ) from exc
    # "Costume already exists" comes back as a 200 with error field —
    # we treat that as idempotent success (caller may be re-adding variants).
    return data


def init_character_via_rest(
    name: str,
    *,
    url: Optional[str] = None,
    timeout: float = 60.0,
) -> dict:
    """Initialize a VNCCS character via the ``/vnccs/create`` REST endpoint.

    Without this call, the CharacterCreator node's ``existing_character``
    dropdown lacks the new name and ``/prompt`` rejects the workflow with
    a ``value_not_in_list`` error. The endpoint also writes the per-character
    config file + creates the on-disk directory tree. Idempotent: returns
    the existing character record if NAME already exists.

    Returns the parsed JSON dict from the endpoint.
    Raises VnccsConnectionError (exit 2) if ComfyUI is unreachable, or
    VnccsExecutionError (exit 4) if the endpoint returns a non-2xx.
    """
    if not name:
        raise VnccsError("character name is required for init")
    base = get_comfy_url(url)
    try:
        with httpx.Client(base_url=base, timeout=timeout) as client:
            response = client.get("/vnccs/create", params={"name": name})
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
    ) as exc:
        raise VnccsConnectionError(
            f"Cannot reach ComfyUI at {base}",
            detail=str(exc),
        ) from exc
    if response.status_code >= 400:
        raise VnccsExecutionError(
            f"VNCCS /vnccs/create failed (HTTP {response.status_code}).",
            detail=response.text[:1000],
        )
    try:
        return response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise VnccsExecutionError(
            "VNCCS /vnccs/create returned non-JSON.",
            detail=str(exc),
        ) from exc


# --- Workflow submission + wait --------------------------------------------


WAIT_POLL_INTERVAL: float = 1.0


def _is_ui_format(workflow: dict) -> bool:
    """UI-format workflow = top-level ``nodes`` list + ``links`` list.

    API format (what /prompt accepts) is a dict keyed by node id → node
    record. Anything with top-level ``nodes``/``links`` arrays must be
    converted via the sibling comfyui skill first.
    """
    return (
        isinstance(workflow, dict)
        and isinstance(workflow.get("nodes"), list)
        and isinstance(workflow.get("links"), list)
    )


def submit_workflow(
    workflow: dict,
    *,
    url: Optional[str] = None,
    client_id: Optional[str] = None,
    timeout: float = 30.0,
) -> dict:
    """POST an API-format workflow to ComfyUI's ``/prompt`` endpoint.

    Returns a dict with keys ``prompt_id``, ``client_id``, ``number``,
    ``node_errors``. Raises:

    - ``VnccsValidationError`` (exit 3) if the workflow is UI-format or
      ComfyUI returns non-empty ``node_errors``.
    - ``VnccsConnectionError`` (exit 2) if the server is unreachable.
    - ``VnccsExecutionError`` (exit 4) if ComfyUI returns HTTP >= 400.
    """
    if _is_ui_format(workflow):
        raise VnccsValidationError(
            "UI-format workflow detected — cannot submit directly.",
            detail=(
                "Convert via the sibling comfyui skill's workflow_run/"
                "graphToPrompt pipeline. See scripts/workflows/README.md."
            ),
        )

    cid = client_id or str(uuid.uuid4())
    base = get_comfy_url(url)
    payload = {"prompt": workflow, "client_id": cid}

    try:
        with httpx.Client(base_url=base, timeout=timeout) as client:
            response = client.post("/prompt", json=payload)
    except (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ) as exc:
        raise VnccsConnectionError(
            f"Cannot reach ComfyUI at {base}",
            detail=str(exc),
        ) from exc

    if response.status_code >= 400:
        try:
            body = response.json()
            detail = json.dumps(body)[:1000]
        except (json.JSONDecodeError, ValueError):
            detail = response.text[:500]
        raise VnccsExecutionError(
            f"ComfyUI rejected workflow (HTTP {response.status_code}).",
            detail=detail,
        )

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise VnccsExecutionError(
            "ComfyUI returned non-JSON response from /prompt.",
            detail=str(exc),
        ) from exc

    node_errors = data.get("node_errors") or {}
    if node_errors:
        raise VnccsValidationError(
            "ComfyUI node validation failed.",
            detail=json.dumps(node_errors)[:1000],
        )

    return {
        "prompt_id": data.get("prompt_id"),
        "client_id": cid,
        "number": data.get("number"),
        "node_errors": node_errors,
    }


def _extract_execution_error_detail(status: dict) -> Optional[str]:
    for ev, payload in status.get("messages") or []:
        if ev == "execution_error" and isinstance(payload, dict):
            msg = payload.get("exception_message")
            etype = payload.get("exception_type")
            if msg:
                return f"[{etype}] {msg}" if etype else str(msg)
    return None


def wait_for_prompt(
    prompt_id: str,
    *,
    url: Optional[str] = None,
    timeout: float = 600.0,
) -> dict:
    """Poll ``GET /history/<prompt_id>`` until the prompt completes.

    Returns the history entry dict on success. Raises:

    - ``VnccsExecutionError`` (exit 4) if the prompt ended with a non-success
      status.
    - ``VnccsConnectionError`` (exit 2) if the server becomes unreachable.
    - ``VnccsError`` (exit 1, generic) if the timeout is exceeded before the
      prompt finishes.
    """
    base = get_comfy_url(url)
    deadline = time.monotonic() + float(timeout)

    with httpx.Client(base_url=base, timeout=10.0) as client:
        while True:
            try:
                response = client.get(f"/history/{prompt_id}")
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
            ) as exc:
                raise VnccsConnectionError(
                    f"Cannot reach ComfyUI at {base}",
                    detail=str(exc),
                ) from exc

            if response.status_code >= 400:
                raise VnccsExecutionError(
                    f"ComfyUI /history returned HTTP {response.status_code}.",
                    detail=response.text[:500],
                )

            try:
                data = response.json()
            except (json.JSONDecodeError, ValueError) as exc:
                raise VnccsExecutionError(
                    "ComfyUI returned non-JSON response from /history.",
                    detail=str(exc),
                ) from exc

            if data:
                entry = data.get(prompt_id) or next(iter(data.values()), {})
                status = entry.get("status") or {}
                status_str = status.get("status_str", "")
                if status_str == "success":
                    return entry
                detail = _extract_execution_error_detail(status)
                raise VnccsExecutionError(
                    f"Prompt {prompt_id} ended with status={status_str!r}.",
                    detail=detail,
                )

            if time.monotonic() >= deadline:
                raise VnccsError(
                    f"Timed out waiting for prompt_id={prompt_id} after {timeout}s.",
                )

            time.sleep(WAIT_POLL_INTERVAL)


# --- Pretty error printing -------------------------------------------------


_stderr = Console(stderr=True)


def print_error_and_exit(err: VnccsError) -> None:
    """Print a VnccsError to stderr via Rich and exit with its exit_code."""
    _stderr.print(f"[bold red]error:[/bold red] {err.message}")
    if err.detail:
        _stderr.print(f"[dim]{err.detail}[/dim]")
    sys.exit(err.exit_code)
