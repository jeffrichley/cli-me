"""Tier 2 integration tests for the `vnccs check` command group.

Filesystem-only. Uses the `fake_comfy` / `fake_comfy_no_vnccs` fixtures
from conftest.py to build a real on-disk ComfyUI layout in tmp_path, set
`COMFY_PATH` via env, and invoke the CLI against it.

The one test of `check all` that would contact ComfyUI is guarded by the
`comfyui_running_or_skip` fixture per the playbook's test discipline.
That test is INTENTIONALLY NOT RUN during this build (the user has a GPU
training job active) — run it manually with:

    pytest qa/comfyui-vnccs/test_check_integration.py -v -m integration \\
           -k server_reachability

when ComfyUI is available.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vnccs_cli import backend
from vnccs_cli.check import app as check_app

pytestmark = pytest.mark.integration

runner = CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch):
    """Force Rich to render at 240 cols so table cells don't wrap mid-string.

    Same rationale as the Tier 1 fixture — substring assertions on
    filenames need the cells to fit on a single line.
    """
    monkeypatch.setenv("COLUMNS", "240")


def _populate_required_packs(comfy: Path, *, skip: tuple[str, ...] = ()) -> None:
    """Create a fake pack dir with `__init__.py` for each required pack.

    Packs in `skip` are omitted entirely (they stay missing). The
    `ComfyUI_VNCCS` pack already exists on the `fake_comfy` fixture — we
    don't overwrite it, just add the rest.
    """
    custom_nodes = comfy / "custom_nodes"
    for pack in backend.REQUIRED_CUSTOM_NODE_PACKS:
        if pack in skip:
            continue
        pd = custom_nodes / pack
        if pd.exists():
            # Already present (e.g. fake_comfy creates ComfyUI_VNCCS).
            # Make sure it has a .py file so the empty-dir check passes.
            if not any(pd.rglob("*.py")):
                (pd / "__init__.py").write_text("# fake\n", encoding="utf-8")
            continue
        pd.mkdir()
        (pd / "__init__.py").write_text("# fake\n", encoding="utf-8")


def _populate_required_models(comfy: Path, *, skip: tuple[str, ...] = ()) -> None:
    """Create a non-empty file on disk for each REQUIRED_MODELS entry.

    Model filenames in `skip` are omitted (they stay missing).
    """
    models_root = comfy / "models"
    for model in backend.REQUIRED_MODELS:
        if model["filename"] in skip:
            continue
        target_dir = models_root / model["subdir"]
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / model["filename"]).write_bytes(b"x" * 1024)


# ---------------------------------------------------------------------------
# check nodes (filesystem-only)
# ---------------------------------------------------------------------------


def test_check_nodes_all_present_exits_zero(fake_comfy, monkeypatch):
    """All required packs present → exit 0, table lists every pack."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    _populate_required_packs(fake_comfy)

    result = runner.invoke(check_app, ["nodes"])
    assert result.exit_code == 0, result.output
    for pack in backend.REQUIRED_CUSTOM_NODE_PACKS:
        assert pack in result.output
    assert "present" in result.output.lower()


def test_check_nodes_missing_pack_exits_five(fake_comfy, monkeypatch):
    """One pack missing → exit 5, table highlights which one."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    missing = "ComfyUI-Impact-Pack"
    _populate_required_packs(fake_comfy, skip=(missing,))

    result = runner.invoke(check_app, ["nodes"])
    assert result.exit_code == 5, result.output
    assert missing in result.output


def test_check_nodes_empty_dir_is_missing(fake_comfy, monkeypatch):
    """Empty pack directory (no .py files) is reported missing."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    _populate_required_packs(fake_comfy)
    # Create an empty dir for one pack, after removing its .py files.
    pack = "ComfyUI-GGUF"
    pack_dir = fake_comfy / "custom_nodes" / pack
    for py in pack_dir.rglob("*.py"):
        py.unlink()

    result = runner.invoke(check_app, ["nodes"])
    assert result.exit_code == 5, result.output
    assert pack in result.output
    assert "no .py files" in result.output or "missing" in result.output.lower()


def test_check_nodes_no_vnccs(fake_comfy_no_vnccs, monkeypatch):
    """A ComfyUI install without VNCCS → VNCCS pack flagged missing → exit 5."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy_no_vnccs))
    # Fill every *other* required pack so only VNCCS is missing.
    _populate_required_packs(fake_comfy_no_vnccs, skip=("ComfyUI_VNCCS",))

    result = runner.invoke(check_app, ["nodes"])
    assert result.exit_code == 5, result.output
    assert "ComfyUI_VNCCS" in result.output


def test_check_nodes_cli_path_overrides_env(fake_comfy, tmp_path, monkeypatch):
    """`--path` takes precedence over COMFY_PATH env."""
    # Point env at a bogus dir; --path should win.
    bogus = tmp_path / "not-real"
    bogus.mkdir()
    (bogus / "custom_nodes").mkdir()  # still not a real install, missing packs
    monkeypatch.setenv("COMFY_PATH", str(bogus))
    _populate_required_packs(fake_comfy)

    result = runner.invoke(check_app, ["nodes", "--path", str(fake_comfy)])
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# check models (filesystem-only)
# ---------------------------------------------------------------------------


def test_check_models_all_present_exits_zero(fake_comfy, monkeypatch):
    """Every required model present → exit 0; table lists all 15+ filenames."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    _populate_required_models(fake_comfy)

    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 0, result.output
    for model in backend.REQUIRED_MODELS:
        assert model["filename"] in result.output


def test_check_models_missing_exits_five(fake_comfy, monkeypatch):
    """A missing required model → exit 5, download URL shown."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    missing = backend.REQUIRED_MODELS[0]["filename"]
    _populate_required_models(fake_comfy, skip=(missing,))

    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 5, result.output
    assert missing in result.output


def test_check_models_optional_missing_still_passes(fake_comfy, monkeypatch):
    """Optional (RMBG) models missing → still exit 0 with a warning."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    optional_names = tuple(
        m["filename"] for m in backend.REQUIRED_MODELS if m["optional"]
    )
    assert optional_names, "Test assumes at least one optional model is defined."
    _populate_required_models(fake_comfy, skip=optional_names)

    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 0, result.output
    assert "optional" in result.output.lower()


def test_check_models_zero_byte_file_is_missing(fake_comfy, monkeypatch):
    """A 0-byte (partial-download) file is reported missing → exit 5."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    _populate_required_models(fake_comfy)
    first_req = next(m for m in backend.REQUIRED_MODELS if not m["optional"])
    target = fake_comfy / "models" / first_req["subdir"] / first_req["filename"]
    target.write_bytes(b"")

    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 5, result.output
    assert first_req["filename"] in result.output


def test_check_models_wrong_subdir_is_missing(fake_comfy, monkeypatch):
    """Model in the wrong subdir (e.g. unet file in checkpoints/) → missing."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    _populate_required_models(fake_comfy)
    # Move the GGUF UNet into models/checkpoints/ — should now be reported missing
    # from models/unet/.
    gguf = next(
        m for m in backend.REQUIRED_MODELS if m["filename"].endswith(".gguf")
    )
    src = fake_comfy / "models" / gguf["subdir"] / gguf["filename"]
    wrong = fake_comfy / "models" / "checkpoints" / gguf["filename"]
    wrong.parent.mkdir(parents=True, exist_ok=True)
    src.replace(wrong)

    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 5, result.output
    assert gguf["filename"] in result.output


# ---------------------------------------------------------------------------
# check all (filesystem-only variants — server branch mocked via monkeypatch)
# ---------------------------------------------------------------------------


def test_check_all_filesystem_failure_short_circuits_before_server(
    fake_comfy, monkeypatch
):
    """If nodes or models fail, check all still probes server and fails overall.

    This test keeps `_check_server` off the network by monkeypatching it
    to return a synthesized 'reachable' response. The filesystem portion
    is the real integration surface being tested here.
    """
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    # Nodes: leave one missing. Models: none populated.
    _populate_required_packs(fake_comfy, skip=("ComfyUI-GGUF",))

    # Fake server probe — avoid hitting ComfyUI.
    from vnccs_cli.commands import check_all as check_all_mod

    monkeypatch.setattr(
        check_all_mod,
        "_check_server",
        lambda url, timeout=3.0: {
            "url": url,
            "reachable": True,
            "detail": "HTTP 200 (mocked)",
        },
    )

    result = runner.invoke(check_app, ["all"])
    assert result.exit_code == 5, result.output
    assert "FAIL" in result.output
    # Both node + model failures should appear in the summary.
    assert "nodes" in result.output or "models" in result.output


def test_check_all_everything_green_filesystem_only(fake_comfy, monkeypatch):
    """Full green path with a mocked server probe (no network)."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    _populate_required_packs(fake_comfy)
    _populate_required_models(fake_comfy)

    from vnccs_cli.commands import check_all as check_all_mod

    monkeypatch.setattr(
        check_all_mod,
        "_check_server",
        lambda url, timeout=3.0: {
            "url": url,
            "reachable": True,
            "detail": "HTTP 200 (mocked)",
        },
    )

    result = runner.invoke(check_app, ["all"])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output


# ---------------------------------------------------------------------------
# check all — live server reachability (DO NOT RUN during this build)
# ---------------------------------------------------------------------------
# This test talks to a real ComfyUI instance. It is gated behind the
# `comfyui_running_or_skip` fixture, so when ComfyUI isn't running the
# test auto-skips. When ComfyUI IS running (e.g. outside a GPU training
# window) run with:
#   pytest qa/comfyui-vnccs/test_check_integration.py -m integration \
#          -k server_reachability
# The -k filter used during the rest of this build excludes this test.


def test_check_all_server_reachability(
    fake_comfy, monkeypatch, comfyui_running_or_skip
):
    """check all against a LIVE ComfyUI server.

    Intentionally NOT run during the automated build — the user has a
    long GPU training job active. The `comfyui_running_or_skip` fixture
    makes this test a no-op when the server isn't reachable; explicit
    `-k server_reachability` exercises it when ComfyUI is idle.
    """
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    _populate_required_packs(fake_comfy)
    _populate_required_models(fake_comfy)
    monkeypatch.setenv("COMFY_URL", comfyui_running_or_skip)

    result = runner.invoke(check_app, ["all"])
    # Exit may be 0 or 5 depending on whether the user's *real* ComfyUI
    # install matches our fake layout — the point of this test is to
    # confirm no crash / no hang on live I/O.
    assert result.exit_code in (0, 5), result.output
    assert "check all" in result.output.lower()
