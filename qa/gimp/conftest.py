from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def gimp_path() -> str:
    candidates = [
        "gimp-console-3.0",
        "gimp-console-2.10",
        "gimp-console",
        "gimp-3.0",
        "gimp-2.10",
        "gimp",
    ]
    for name in candidates:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    pytest.skip("GIMP executable not available on PATH; skipping integration/manual tests.")


@pytest.fixture
def tmp_script_file(tmp_path: Path) -> Path:
    script = tmp_path / "quit.scm"
    script.write_text('(gimp-quit 0)\n', encoding="utf-8")
    return script
