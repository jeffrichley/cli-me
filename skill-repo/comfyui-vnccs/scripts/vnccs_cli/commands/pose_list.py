"""Logic for `vnccs pose list` — enumerate bundled pose presets.

Pure filesystem enumeration of `<VNCCS_INSTALL>/presets/poses/`. No HTTP
calls. VNCCS ships pose presets as JSON files (each one describes a
BODY_25 skeleton), not as images — the stock install has
`vnccs_poseset.json` with 12 poses. This matches what the VNCCS REST
endpoint `/vnccs/pose_presets` enumerates (see `__init__.py:180-199` in
the VNCCS node pack).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from vnccs_cli.backend import get_vnccs_install_dir

SUPPORTED_EXTENSIONS = {".json"}


def run_list(*, comfy_path: Optional[str] = None) -> list[dict]:
    """Return a sorted list of pose preset files.

    Each entry is {"name": str, "size": int} where `size` is the file's
    byte count. Sorted by filename ascending. Returns an empty list if
    the `presets/poses/` directory is missing or has no image files —
    this is not an error (fresh VNCCS installs may ship without presets).

    Raises:
        VnccsPathError: COMFY_PATH unresolvable or VNCCS not installed.
    """
    vnccs = get_vnccs_install_dir(comfy_path)
    poses_dir = vnccs / "presets" / "poses"

    if not poses_dir.is_dir():
        return []

    entries: list[dict] = []
    for entry in poses_dir.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            size = entry.stat().st_size
        except OSError:
            # Racing-delete / permission error — skip rather than crash.
            continue
        entries.append({"name": entry.name, "size": size})

    entries.sort(key=lambda e: e["name"])
    return entries
