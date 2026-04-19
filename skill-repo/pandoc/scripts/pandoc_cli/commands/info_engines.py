"""Logic for `info engines` — partition PDF engines into available/missing."""

from __future__ import annotations

import shutil

from pandoc_cli.backend import PDF_ENGINES


def run_engines() -> dict[str, list[str]]:
    """Probe each engine in ``backend.PDF_ENGINES`` against PATH.

    Returns
    -------
    dict
        ``{"available": [...], "missing": [...]}``. Order matches
        ``backend.PDF_ENGINES`` within each list.
    """
    available: list[str] = []
    missing: list[str] = []
    for engine in PDF_ENGINES:
        if shutil.which(engine) is not None:
            available.append(engine)
        else:
            missing.append(engine)
    return {"available": available, "missing": missing}
