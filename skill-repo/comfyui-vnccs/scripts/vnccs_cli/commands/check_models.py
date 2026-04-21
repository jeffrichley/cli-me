"""Logic for `vnccs check models` — verify required model files on disk.

Per playbook.md §check models:
- Cross-reference `backend.REQUIRED_MODELS` against actual files on disk.
- A model is "missing" if the file doesn't exist at any candidate path.
- Searches both ``<COMFY_PATH>/models/`` AND every directory listed in
  ``<COMFY_PATH>/extra_model_paths.yaml`` (ComfyUI's standard mechanism
  for redirecting model dirs — bug fixed when a real install was found
  with all models living at ``E:/data/comfy/models/``).
- A partial-download file (size 0) is also treated as missing.
- Optional entries (e.g. RMBG variants) warn but don't fail — they are
  tagged `optional=True` in the report so the caller can decide exit code.
"""

from __future__ import annotations

from typing import Optional

from vnccs_cli.backend import REQUIRED_MODELS, find_model_path, get_comfy_path


def run_check_models(*, comfy_path: Optional[str] = None) -> list[dict]:
    """Check every required model and return a structured report.

    Each entry: {
        "filename": str,
        "type": str,
        "subdir": str,
        "full_path": str,    # the location where the file was FOUND, or
                             # the canonical default if missing
        "present": bool,
        "download_url": str,
        "optional": bool,
    }.

    Raises:
        VnccsPathError: COMFY_PATH unset / not a ComfyUI install (exit 6).
    """
    comfy = get_comfy_path(comfy_path)

    results: list[dict] = []
    for model in REQUIRED_MODELS:
        full_path, present = find_model_path(
            comfy, model["subdir"], model["filename"]
        )
        results.append(
            {
                "filename": model["filename"],
                "type": model["type"],
                "subdir": model["subdir"],
                "full_path": str(full_path),
                "present": present,
                "download_url": model["download_url"],
                "optional": model["optional"],
            }
        )
    return results
