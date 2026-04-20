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
