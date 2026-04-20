"""Tier 1 tests for the `vnccs check` command group.

Filesystem access is mocked via pytest monkeypatch on Path methods / the
module-level `REQUIRED_*` constants. HTTP calls are mocked via
pytest-httpx. No real ComfyUI process or real ComfyUI install is
required.

Each command has a "kitchen-sink" test that exercises every branch
(all-present / some-missing / all-missing / bad-path) in one place per
SWOT W1.
"""

from __future__ import annotations

from typing import Optional

import httpx
import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from vnccs_cli import backend
from vnccs_cli.check import app as check_app
from vnccs_cli.commands import check_all as check_all_mod
from vnccs_cli.commands import check_models as check_models_mod
from vnccs_cli.commands import check_nodes as check_nodes_mod

pytestmark = pytest.mark.command_graph

runner = CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch):
    """Force Rich to render at 240 cols so table cells don't wrap mid-string.

    Rich reads `COLUMNS` from the environment when no explicit width is
    passed to Console(). Tests assert on filenames/URLs via substring —
    if Rich wraps those strings across multiple rows, the substring
    check fails even though the value is logically present. A very wide
    terminal keeps each cell on one line.
    """
    monkeypatch.setenv("COLUMNS", "240")


def _flat(output: str) -> str:
    """Strip Rich table box-drawing + whitespace so wrapped strings concatenate.

    Rich wraps long filenames/URLs across several cells in the rendered
    table (e.g. `qwen-image-ed` / `it-2511-Q5_0.` / `gguf`). Tests care
    that the full string is *logically* present, not visually. Flatten
    by removing every table border char + any whitespace.
    """
    for ch in ("│", "─", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼", "…"):
        output = output.replace(ch, "")
    # Collapse all whitespace (including internal wraps) to the empty string.
    return "".join(output.split())


# ---------------------------------------------------------------------------
# Contract tests for the REQUIRED_MODELS list itself.
# ---------------------------------------------------------------------------


def test_required_models_includes_seedvr2_dit_and_vae():
    """SeedVR2 needs BOTH the DiT and its matched VAE — upstream workflows
    (see references/source-analysis/workflow-stages.md:99-101, 135-136)
    load both files at the same subgraph. A missing VAE entry meant
    `check models` reported green on installs that would crash at
    upscale-time. Pin the pair so regressions surface (r3/check HIGH fix).
    """
    filenames = {entry["filename"] for entry in backend.REQUIRED_MODELS}
    assert "seedvr2_ema_3b_fp16.safetensors" in filenames
    assert "ema_vae_fp16.safetensors" in filenames
    # Both required (not optional).
    by_name = {e["filename"]: e for e in backend.REQUIRED_MODELS}
    assert by_name["seedvr2_ema_3b_fp16.safetensors"]["optional"] is False
    assert by_name["ema_vae_fp16.safetensors"]["optional"] is False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeGetComfyPath:
    """Callable stand-in for `backend.get_comfy_path`.

    Returns `tmp_path / "ComfyUI"` unless `raise_error` is set, in which
    case it raises `VnccsPathError` so tests can exercise the
    path-missing branch.
    """

    def __init__(self, comfy_root, *, raise_error: Optional[Exception] = None) -> None:
        self.comfy_root = comfy_root
        self.raise_error = raise_error
        self.calls: list[Optional[str]] = []

    def __call__(self, cli_path: Optional[str] = None):
        self.calls.append(cli_path)
        if self.raise_error is not None:
            raise self.raise_error
        return self.comfy_root


def _patch_backend_paths(monkeypatch, comfy_root, *, raise_error=None):
    """Monkeypatch `get_comfy_path` everywhere the check modules look it up."""
    fake = _FakeGetComfyPath(comfy_root, raise_error=raise_error)
    monkeypatch.setattr(check_nodes_mod, "get_comfy_path", fake)
    monkeypatch.setattr(check_models_mod, "get_comfy_path", fake)
    return fake


# ---------------------------------------------------------------------------
# check nodes
# ---------------------------------------------------------------------------


def test_check_nodes_kitchen_sink(monkeypatch, tmp_path):
    """Kitchen-sink for `check nodes`: every parameter branch in one test.

    Branches exercised:
      1. All required packs present → exit 0
      2. Some packs missing (both "dir missing" + "empty dir" reasons) → exit 5
      3. All packs missing → exit 5
      4. bad COMFY_PATH (VnccsPathError) → exit 6
    """

    # --- Branch 1: all packs present -------------------------------------
    comfy = tmp_path / "happy"
    (comfy / "custom_nodes").mkdir(parents=True)
    for pack in backend.REQUIRED_CUSTOM_NODE_PACKS:
        pack_dir = comfy / "custom_nodes" / pack
        pack_dir.mkdir()
        (pack_dir / "__init__.py").write_text("# fake\n", encoding="utf-8")

    _patch_backend_paths(monkeypatch, comfy)
    result = runner.invoke(check_app, ["nodes"])
    assert result.exit_code == 0, result.output
    assert "all" in result.output.lower() and "present" in result.output.lower()
    flat = _flat(result.output)
    for pack in backend.REQUIRED_CUSTOM_NODE_PACKS:
        assert pack in flat

    # --- Branch 2: some missing (dir missing + empty dir both covered) ---
    comfy2 = tmp_path / "mixed"
    (comfy2 / "custom_nodes").mkdir(parents=True)
    for i, pack in enumerate(backend.REQUIRED_CUSTOM_NODE_PACKS):
        pack_dir = comfy2 / "custom_nodes" / pack
        if i == 0:
            # dir missing entirely
            continue
        if i == 1:
            # empty dir (no .py files) — treated as missing
            pack_dir.mkdir()
            continue
        pack_dir.mkdir()
        (pack_dir / "__init__.py").write_text("# fake\n", encoding="utf-8")

    _patch_backend_paths(monkeypatch, comfy2)
    result = runner.invoke(check_app, ["nodes"])
    assert result.exit_code == 5, result.output
    assert "missing" in result.output.lower()
    # Both failure reasons should have been surfaced by run_check_nodes.
    assert "directory missing" in result.output or "no .py files" in result.output

    # --- Branch 3: all missing ------------------------------------------
    comfy3 = tmp_path / "empty"
    (comfy3 / "custom_nodes").mkdir(parents=True)
    _patch_backend_paths(monkeypatch, comfy3)
    result = runner.invoke(check_app, ["nodes"])
    assert result.exit_code == 5, result.output
    # Every pack should be flagged missing in the output.
    flat = _flat(result.output)
    for pack in backend.REQUIRED_CUSTOM_NODE_PACKS:
        assert pack in flat

    # --- Branch 4: bad COMFY_PATH → exit 6 ------------------------------
    err = backend.VnccsPathError("COMFY_PATH not set.", detail="unit-test")
    _patch_backend_paths(monkeypatch, tmp_path, raise_error=err)
    result = runner.invoke(check_app, ["nodes"])
    assert result.exit_code == 6, result.output


def test_check_nodes_honors_cli_path_flag(monkeypatch, tmp_path):
    """`--path` is forwarded to `get_comfy_path` (precedence over env)."""
    comfy = tmp_path / "ComfyUI"
    (comfy / "custom_nodes").mkdir(parents=True)
    for pack in backend.REQUIRED_CUSTOM_NODE_PACKS:
        pack_dir = comfy / "custom_nodes" / pack
        pack_dir.mkdir()
        (pack_dir / "__init__.py").write_text("# fake\n", encoding="utf-8")

    fake = _patch_backend_paths(monkeypatch, comfy)
    result = runner.invoke(check_app, ["nodes", "--path", str(comfy)])
    assert result.exit_code == 0, result.output
    assert fake.calls and fake.calls[-1] == str(comfy)


# ---------------------------------------------------------------------------
# check models
# ---------------------------------------------------------------------------


def _make_models_layout(comfy_root, which_present: str) -> None:
    """Populate fake model files under `comfy_root/models/`.

    which_present:
      - "all": every REQUIRED_MODELS entry present (non-zero size)
      - "required_only": required models present, optional missing
      - "some": first required missing, rest present
      - "none": no model files
    """
    models_root = comfy_root / "models"
    models_root.mkdir(parents=True, exist_ok=True)
    if which_present == "none":
        return
    for i, model in enumerate(backend.REQUIRED_MODELS):
        if which_present == "some" and i == 0:
            continue
        if which_present == "required_only" and model["optional"]:
            continue
        target_dir = models_root / model["subdir"]
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / model["filename"]).write_bytes(b"x" * 1024)


def test_check_models_kitchen_sink(monkeypatch, tmp_path):
    """Kitchen-sink for `check models`: exercise every branch.

    Branches:
      1. All models present → exit 0
      2. Required present, optional missing → exit 0 + warning
      3. Some required missing → exit 5
      4. All missing → exit 5
      5. Partial-download (0-byte) required file → exit 5
      6. bad COMFY_PATH → exit 6
    """

    # Branch 1: all present ------------------------------------------------
    comfy1 = tmp_path / "all"
    _make_models_layout(comfy1, "all")
    _patch_backend_paths(monkeypatch, comfy1)
    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 0, result.output
    # The table should list every required filename.
    flat = _flat(result.output)
    for model in backend.REQUIRED_MODELS:
        assert model["filename"] in flat

    # Branch 2: required-only; optional missing ---------------------------
    comfy2 = tmp_path / "required_only"
    _make_models_layout(comfy2, "required_only")
    _patch_backend_paths(monkeypatch, comfy2)
    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 0, result.output
    assert "optional" in result.output.lower()

    # Branch 3: one required missing --------------------------------------
    comfy3 = tmp_path / "some"
    _make_models_layout(comfy3, "some")
    _patch_backend_paths(monkeypatch, comfy3)
    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 5, result.output
    assert backend.REQUIRED_MODELS[0]["filename"] in _flat(result.output)

    # Branch 4: all missing -----------------------------------------------
    comfy4 = tmp_path / "none"
    _make_models_layout(comfy4, "none")
    _patch_backend_paths(monkeypatch, comfy4)
    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 5, result.output

    # Branch 5: partial-download (0-byte required file) -------------------
    comfy5 = tmp_path / "partial"
    _make_models_layout(comfy5, "all")
    # Zero out the first required model's file.
    first_req = next(m for m in backend.REQUIRED_MODELS if not m["optional"])
    target = comfy5 / "models" / first_req["subdir"] / first_req["filename"]
    target.write_bytes(b"")
    _patch_backend_paths(monkeypatch, comfy5)
    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 5, result.output

    # Branch 6: bad COMFY_PATH → exit 6 -----------------------------------
    err = backend.VnccsPathError("COMFY_PATH not set.", detail="unit-test")
    _patch_backend_paths(monkeypatch, tmp_path, raise_error=err)
    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 6, result.output


def test_check_models_missing_shows_download_url(monkeypatch, tmp_path):
    """A missing required model's download URL is surfaced in the table."""
    comfy = tmp_path / "ComfyUI"
    _make_models_layout(comfy, "none")
    _patch_backend_paths(monkeypatch, comfy)

    result = runner.invoke(check_app, ["models"])
    assert result.exit_code == 5, result.output
    # At least one non-optional model's URL should be printed. Rich wraps
    # long URLs across multiple cells — flatten before checking.
    first_req = next(m for m in backend.REQUIRED_MODELS if not m["optional"])
    flat = _flat(result.output)
    url_prefix = first_req["download_url"].split("/")[2]  # domain
    assert url_prefix in flat


# ---------------------------------------------------------------------------
# check all
# ---------------------------------------------------------------------------


def test_check_all_kitchen_sink(monkeypatch, tmp_path, httpx_mock: HTTPXMock):
    """Kitchen-sink for `check all`: every branch in one test.

    Branches:
      1. Everything green (nodes+models present, server 200) → exit 0
      2. Nodes fail, rest green → exit 5
      3. Models fail, rest green → exit 5
      4. Server unreachable, rest green → exit 5
      5. bad COMFY_PATH → exit 6
    """

    # --- shared fixture: a fully-populated fake ComfyUI ------------------
    def _make_happy_path(name: str):
        comfy = tmp_path / name
        (comfy / "custom_nodes").mkdir(parents=True)
        for pack in backend.REQUIRED_CUSTOM_NODE_PACKS:
            pd = comfy / "custom_nodes" / pack
            pd.mkdir()
            (pd / "__init__.py").write_text("# fake\n", encoding="utf-8")
        _make_models_layout(comfy, "all")
        return comfy

    url = backend.get_comfy_url()

    # Branch 1: everything green ------------------------------------------
    comfy1 = _make_happy_path("green")
    _patch_backend_paths(monkeypatch, comfy1)
    httpx_mock.add_response(url=f"{url}/system_stats", json={"ok": True})
    result = runner.invoke(check_app, ["all"])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output

    # Branch 2: nodes fail ------------------------------------------------
    comfy2 = _make_happy_path("nodes_fail")
    # Remove one pack to trigger failure.
    import shutil as _shutil
    _shutil.rmtree(comfy2 / "custom_nodes" / backend.REQUIRED_CUSTOM_NODE_PACKS[0])
    _patch_backend_paths(monkeypatch, comfy2)
    httpx_mock.add_response(url=f"{url}/system_stats", json={"ok": True})
    result = runner.invoke(check_app, ["all"])
    assert result.exit_code == 5, result.output
    assert "FAIL" in result.output
    assert "nodes" in result.output

    # Branch 3: models fail -----------------------------------------------
    comfy3 = _make_happy_path("models_fail")
    first_req = next(m for m in backend.REQUIRED_MODELS if not m["optional"])
    (comfy3 / "models" / first_req["subdir"] / first_req["filename"]).unlink()
    _patch_backend_paths(monkeypatch, comfy3)
    httpx_mock.add_response(url=f"{url}/system_stats", json={"ok": True})
    result = runner.invoke(check_app, ["all"])
    assert result.exit_code == 5, result.output
    assert "models" in result.output

    # Branch 4: server unreachable ----------------------------------------
    comfy4 = _make_happy_path("server_fail")
    _patch_backend_paths(monkeypatch, comfy4)
    # Simulate a connection error from httpx.
    httpx_mock.add_exception(httpx.ConnectError("refused"), url=f"{url}/system_stats")
    result = runner.invoke(check_app, ["all"])
    assert result.exit_code == 5, result.output
    assert "server" in result.output
    assert "unreachable" in result.output.lower()

    # Branch 5: bad COMFY_PATH → exit 6 -----------------------------------
    err = backend.VnccsPathError("COMFY_PATH not set.", detail="unit-test")
    _patch_backend_paths(monkeypatch, tmp_path, raise_error=err)
    # No httpx mock needed — the VnccsPathError fires before server probe.
    result = runner.invoke(check_app, ["all"])
    assert result.exit_code == 6, result.output


def test_check_all_server_http_error_counts_as_unreachable(
    monkeypatch, tmp_path, httpx_mock: HTTPXMock
):
    """A non-2xx response on /system_stats is treated as server-unreachable."""
    comfy = tmp_path / "ComfyUI"
    (comfy / "custom_nodes").mkdir(parents=True)
    for pack in backend.REQUIRED_CUSTOM_NODE_PACKS:
        pd = comfy / "custom_nodes" / pack
        pd.mkdir()
        (pd / "__init__.py").write_text("# fake\n", encoding="utf-8")
    _make_models_layout(comfy, "all")
    _patch_backend_paths(monkeypatch, comfy)

    url = backend.get_comfy_url()
    httpx_mock.add_response(url=f"{url}/system_stats", status_code=503)

    result = runner.invoke(check_app, ["all"])
    assert result.exit_code == 5, result.output
    assert "server" in result.output
    assert "HTTP 503" in result.output


# ---------------------------------------------------------------------------
# Logic-layer unit tests (don't touch Typer at all — faster feedback)
# ---------------------------------------------------------------------------


def test_run_check_nodes_empty_dir_is_missing(monkeypatch, tmp_path):
    """An empty pack dir (no .py files) is reported missing per playbook."""
    comfy = tmp_path / "ComfyUI"
    (comfy / "custom_nodes").mkdir(parents=True)
    for pack in backend.REQUIRED_CUSTOM_NODE_PACKS:
        (comfy / "custom_nodes" / pack).mkdir()
    _patch_backend_paths(monkeypatch, comfy)

    rows = check_nodes_mod.run_check_nodes()
    assert all(not r["present"] for r in rows)
    assert all(r["reason"] == "no .py files" for r in rows)


def test_run_check_models_zero_byte_file_is_missing(monkeypatch, tmp_path):
    """A 0-byte model file (partial download) is reported missing."""
    comfy = tmp_path / "ComfyUI"
    _make_models_layout(comfy, "all")
    # Zero-out the first required model.
    first_req = next(m for m in backend.REQUIRED_MODELS if not m["optional"])
    (comfy / "models" / first_req["subdir"] / first_req["filename"]).write_bytes(b"")
    _patch_backend_paths(monkeypatch, comfy)

    rows = check_models_mod.run_check_models()
    zeroed = next(r for r in rows if r["filename"] == first_req["filename"])
    assert zeroed["present"] is False


def test_check_server_handles_various_errors(monkeypatch):
    """`_check_server` maps all network errors to reachable=False."""

    # Connection error → not reachable.
    def _raise_connect(url, timeout):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(check_all_mod.httpx, "get", _raise_connect)
    result = check_all_mod._check_server("http://127.0.0.1:8188")
    assert result["reachable"] is False
    assert "ConnectError" in result["detail"]

    # Timeout → not reachable.
    def _raise_timeout(url, timeout):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(check_all_mod.httpx, "get", _raise_timeout)
    result = check_all_mod._check_server("http://127.0.0.1:8188")
    assert result["reachable"] is False

    # 200 response → reachable.
    class _Resp:
        status_code = 200

    monkeypatch.setattr(check_all_mod.httpx, "get", lambda url, timeout: _Resp())
    result = check_all_mod._check_server("http://127.0.0.1:8188")
    assert result["reachable"] is True
    assert "HTTP 200" in result["detail"]

    # 503 response → not reachable.
    class _Resp503:
        status_code = 503

    monkeypatch.setattr(check_all_mod.httpx, "get", lambda url, timeout: _Resp503())
    result = check_all_mod._check_server("http://127.0.0.1:8188")
    assert result["reachable"] is False
    assert "HTTP 503" in result["detail"]
