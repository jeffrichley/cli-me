"""Shared fixtures for comfyui-vnccs QA tests.

Session-scoped fixtures skip cleanly when ComfyUI / VNCCS / a model / a
custom-node pack is missing. Per-test content fixtures build a fake
ComfyUI filesystem layout in tmp_path so tests can run without touching
the real install.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

# Make the skill's scripts/ importable so `from vnccs_cli...` resolves.
_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "skill-repo"
    / "comfyui-vnccs"
    / "scripts"
)
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Add qa/comfyui-vnccs/ so test files can `from _vnccs_helpers import ...`
# (importlib mode doesn't auto-add the test dir). Skill-prefixed to avoid
# colliding with the sibling qa/comfyui/_pandoc_helpers.py etc.
_QA_DIR = Path(__file__).resolve().parent
if str(_QA_DIR) not in sys.path:
    sys.path.insert(0, str(_QA_DIR))


# ---------------------------------------------------------------------------
# Real-install probes (session-scoped; skip when missing)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def comfy_path_or_skip() -> Path:
    """Resolved COMFY_PATH or pytest.skip. Reuses the wrapper's logic."""
    from vnccs_cli import backend

    try:
        return backend.get_comfy_path()
    except backend.VnccsPathError as e:
        pytest.skip(f"COMFY_PATH not usable: {e.message}")


@pytest.fixture(scope="session")
def vnccs_install_or_skip(comfy_path_or_skip: Path) -> Path:
    """Resolved VNCCS install dir or skip."""
    from vnccs_cli import backend

    try:
        return backend.get_vnccs_install_dir(str(comfy_path_or_skip))
    except backend.VnccsPathError as e:
        pytest.skip(f"VNCCS not installed: {e.message}")


@pytest.fixture(scope="session")
def comfyui_running_or_skip(comfy_path_or_skip: Path) -> str:
    """ComfyUI server reachable at COMFY_URL, else skip.

    Does a cheap GET /system_stats via httpx. Returns the base URL on success.
    """
    import httpx
    from vnccs_cli import backend

    url = backend.get_comfy_url()
    try:
        httpx.get(f"{url}/system_stats", timeout=3.0)
    except Exception:
        pytest.skip(f"ComfyUI not running at {url}")
    return url


# ---------------------------------------------------------------------------
# Fake ComfyUI filesystem (per-test; no network)
# ---------------------------------------------------------------------------


def _make_fake_comfy(root: Path, *, with_vnccs: bool = True) -> Path:
    """Build a minimal fake ComfyUI install in `root` and return it.

    Creates custom_nodes/, models/, main.py, and (optionally) a fake
    ComfyUI_VNCCS directory with the minimum structure the wrapper probes.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "custom_nodes").mkdir(exist_ok=True)
    (root / "models").mkdir(exist_ok=True)
    (root / "output").mkdir(exist_ok=True)
    (root / "main.py").write_text("# fake comfy\n", encoding="utf-8")

    if with_vnccs:
        vnccs = root / "custom_nodes" / "ComfyUI_VNCCS"
        vnccs.mkdir(exist_ok=True)
        (vnccs / "nodes").mkdir(exist_ok=True)
        (vnccs / "workflows").mkdir(exist_ok=True)
        (vnccs / "presets" / "poses").mkdir(parents=True, exist_ok=True)
        (vnccs / "emotions-config" / "images").mkdir(parents=True, exist_ok=True)
        (vnccs / "__init__.py").write_text("# fake vnccs\n", encoding="utf-8")
        (vnccs / "pyproject.toml").write_text(
            '[project]\nname = "vnccs"\nversion = "2.1.0"\n', encoding="utf-8"
        )

    return root


@pytest.fixture
def fake_comfy(tmp_path: Path) -> Path:
    """Per-test fake ComfyUI install in tmp_path. VNCCS pre-populated."""
    return _make_fake_comfy(tmp_path / "ComfyUI")


@pytest.fixture
def fake_comfy_no_vnccs(tmp_path: Path) -> Path:
    """Per-test fake ComfyUI install with custom_nodes/ but no VNCCS."""
    return _make_fake_comfy(tmp_path / "ComfyUI", with_vnccs=False)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Opt-in fixture that clears COMFY_PATH / COMFY_URL for the current test.

    NOT autouse — tests that use the real-install probes
    (`comfy_path_or_skip`, etc.) need those env vars set. Tests that want
    a clean slate to exercise the "unset env" code paths request this
    fixture explicitly:

        def test_unset_path_raises(clean_env, tmp_path): ...

    Why not autouse: pytest's monkeypatch is function-scoped and tears
    down at test end, but a session-scoped fixture instantiated lazily
    from inside a test gets the monkeypatched env during its computation.
    An autouse `delenv` would silently convert every real-install
    integration test into a perma-skip.
    """
    monkeypatch.delenv("COMFY_PATH", raising=False)
    monkeypatch.delenv("COMFY_URL", raising=False)


# ---------------------------------------------------------------------------
# Bundled workflow access (for tests that verify the workflow bundle integrity)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def bundled_workflows_dir() -> Path:
    """Path to the bundled workflows directory (scripts/workflows/)."""
    return _SCRIPTS_DIR / "workflows"
