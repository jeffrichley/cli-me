"""workflow extract — pull embedded workflow from PNG (tEXt/iTXt) or WebP (EXIF).

Per references/techniques/workflow-formats.md:

- PNG: `Image.open(p).info["prompt"]` (API) / `.info["workflow"]` (UI).
- WebP: scan EXIF tag `0x0110` (prompt) and descending from `0x010F`
  (workflow, tag order depends on extra_pnginfo dict iteration).
- Handle bytes-vs-str return from Pillow.
- Exit code 5 when no embedded workflow is present.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from comfyui_cli.backend import ComfyError, ComfyNotFoundError


_NO_WORKFLOW_MSG = (
    "No embedded workflow found. Was ComfyUI started with --disable-metadata, "
    "or did a custom SaveImage node strip it? Try a different image."
)


def _decode(value: Any) -> Optional[str]:
    """Normalize chunk / EXIF values to str. None for missing."""
    if value is None:
        return None
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _load_json_chunk(value: Any) -> Optional[dict]:
    text = _decode(value)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _parse_prefixed(value: Any, prefix: str) -> Optional[dict]:
    """Parse 'prefix:<json>' EXIF values per workflow-formats.md."""
    text = _decode(value)
    if not text or not text.startswith(prefix + ":"):
        return None
    _, _, payload = text.partition(":")
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _extract_png(path: Path) -> tuple[Optional[dict], Optional[dict]]:
    with Image.open(path) as img:
        info = dict(img.info)
    return (
        _load_json_chunk(info.get("prompt")),
        _load_json_chunk(info.get("workflow")),
    )


def _extract_webp(path: Path) -> tuple[Optional[dict], Optional[dict]]:
    with Image.open(path) as img:
        exif = img.getexif()

    api = _parse_prefixed(exif.get(0x0110), "prompt")

    ui: Optional[dict] = None
    # Scan descending from 0x010F (tag order depends on extra_pnginfo dict
    # iteration, so we don't hardcode 0x010F).
    for tag in range(0x010F, 0x010F - 16, -1):
        ui = _parse_prefixed(exif.get(tag), "workflow")
        if ui is not None:
            break

    return api, ui


def _load_workflows(path: Path) -> tuple[Optional[dict], Optional[dict]]:
    """Return (api, ui) workflows extracted from path. Either may be None."""
    suffix = path.suffix.lower()
    if suffix == ".png":
        return _extract_png(path)
    if suffix == ".webp":
        return _extract_webp(path)
    # Fall back: try PNG first then WebP by content probe.
    try:
        return _extract_png(path)
    except Exception:
        try:
            return _extract_webp(path)
        except Exception as exc:
            raise ComfyError(
                f"Could not read image {path}: unsupported format.",
                detail=str(exc),
            ) from exc


def extract_api_dict(image: Path) -> dict:
    """Extract the embedded API-format workflow dict from an image.

    Pure function — no stdout/file IO. Raises ComfyError if the image cannot
    be read; raises ComfyNotFoundError (exit 5) if no API workflow is
    embedded. Reused by `workflow run` for PNG/WebP inputs.
    """
    if not image.exists():
        raise ComfyError(f"Image not found: {image}")
    api_wf, _ = _load_workflows(image)
    if api_wf is None:
        raise ComfyNotFoundError(_NO_WORKFLOW_MSG)
    return api_wf


def run_extract(
    *,
    image: Path,
    ui: bool,
    api: bool,
    both: bool,
    out_file: Optional[Path],
) -> None:
    """Extract embedded workflow(s) from image, write to out_file or stdout."""
    # Enforce mutual exclusivity of --ui / --api / --both.
    flag_count = sum(1 for f in (ui, api, both) if f)
    if flag_count > 1:
        raise ComfyError("--ui, --api, --both are mutually exclusive.")

    if not image.exists():
        raise ComfyError(f"Image not found: {image}")

    api_wf, ui_wf = _load_workflows(image)

    if both:
        if api_wf is None and ui_wf is None:
            raise ComfyNotFoundError(_NO_WORKFLOW_MSG)
        payload: Any = {"api": api_wf, "ui": ui_wf}
    elif ui:
        if ui_wf is None:
            raise ComfyNotFoundError(_NO_WORKFLOW_MSG)
        payload = ui_wf
    else:
        # Default: --api
        if api_wf is None:
            raise ComfyNotFoundError(_NO_WORKFLOW_MSG)
        payload = api_wf

    rendered = json.dumps(payload, indent=2) + "\n"

    if out_file is not None:
        out_file.write_text(rendered)
    else:
        sys.stdout.write(rendered)
        sys.stdout.flush()


# Backwards-compatibility alias
def run_workflow_extract(
    *,
    image: Path,
    ui: bool = False,
    api: bool = False,
    both: bool = False,
    output: Optional[Path] = None,
) -> None:
    run_extract(image=image, ui=ui, api=api, both=both, out_file=output)
