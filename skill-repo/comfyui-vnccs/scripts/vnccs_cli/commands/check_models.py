"""Logic for `vnccs check models` — verify required model files on disk.

Per playbook.md §check models:
- Cross-reference `backend.REQUIRED_MODELS` against the actual files on
  disk under `<COMFY_PATH>/models/`.
- A model is "missing" if the file doesn't exist at its expected subdir.
- A partial-download file (size 0) is also treated as missing.
- Optional entries (e.g. RMBG variants) warn but don't fail — they are
  tagged `optional=True` in the report so the caller can decide exit code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from vnccs_cli.backend import REQUIRED_MODELS, get_comfy_path


def _model_present(full_path: Path) -> bool:
    """True iff the model file exists and is non-empty on disk.

    A 0-byte file is treated as missing (partial-download guard per
    playbook.md §check models edge cases). OS errors (e.g. permission
    denied) are reported as missing — the user will see the file path
    in the table and can diagnose.
    """
    try:
        if not full_path.is_file():
            return False
        return full_path.stat().st_size > 0
    except OSError:
        return False


def run_check_models(*, comfy_path: Optional[str] = None) -> list[dict]:
    """Check every required model and return a structured report.

    Each entry: {
        "filename": str,
        "type": str,
        "subdir": str,
        "full_path": str,
        "present": bool,
        "download_url": str,
        "optional": bool,
    }.

    Raises:
        VnccsPathError: COMFY_PATH unset / not a ComfyUI install (exit 6).
    """
    comfy = get_comfy_path(comfy_path)
    models_root = comfy / "models"

    results: list[dict] = []
    for model in REQUIRED_MODELS:
        full_path = models_root / model["subdir"] / model["filename"]
        present = _model_present(full_path)
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
