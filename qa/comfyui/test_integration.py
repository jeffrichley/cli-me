"""Tier 2 integration tests — hit a live ComfyUI server.

Skipped automatically if no server is reachable at COMFY_URL (default
http://127.0.0.1:8188). Tagged with the `integration` pytest marker.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import httpx
import pytest

scripts_dir = (
    Path(__file__).resolve().parent.parent.parent
    / "skill-repo"
    / "comfyui"
    / "scripts"
)
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))


COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")


def _server_alive() -> bool:
    try:
        with httpx.Client(timeout=3.0, headers={"Origin": COMFY_URL}) as c:
            return c.get(f"{COMFY_URL}/system_stats").status_code == 200
    except Exception:
        return False


skip_no_server = pytest.mark.skipif(
    not _server_alive(), reason="No live ComfyUI server"
)
pytestmark = pytest.mark.integration


@skip_no_server
class TestPingLive:
    def test_real_server_returns_ok(self, capsys):
        from comfyui_cli.commands.ping import run_ping

        run_ping(url=COMFY_URL, timeout=10.0)
        out = capsys.readouterr().out
        assert "ok" in out.lower()

    def test_real_server_mentions_version(self, capsys):
        from comfyui_cli.commands.ping import run_ping

        run_ping(url=COMFY_URL, timeout=10.0)
        out = capsys.readouterr().out
        # Some semver-ish version number appears in the ping line.
        assert "ComfyUI" in out
        # Crude: at least one digit.
        assert any(ch.isdigit() for ch in out)


@skip_no_server
class TestInfoLive:
    def test_real_server_has_expected_keys(self, capsys):
        from comfyui_cli.commands.info import run_info

        run_info(url=COMFY_URL, timeout=10.0, json_output=True)
        out = capsys.readouterr().out
        data = json.loads(out)

        # Deep structural assertions — "nonzero output" is not enough.
        assert "system" in data
        assert "devices" in data

        sys_block = data["system"]
        assert "comfyui_version" in sys_block
        assert "pytorch_version" in sys_block
        assert "python_version" in sys_block
        assert "ram_total" in sys_block

        # ComfyUI-specific shape — version is semver-ish (e.g. "0.19.0").
        assert re.match(r"^\d+\.\d+", sys_block["comfyui_version"])
        # PyTorch version always carries a build tag: "+cuNNN", "+cpu", or
        # similar. Accept either "+" or a "cu"/"cpu" substring.
        pytorch_ver = sys_block["pytorch_version"].lower()
        assert "+" in pytorch_ver or "cu" in pytorch_ver or "cpu" in pytorch_ver
        # The real server always emits argv as a list.
        assert isinstance(sys_block["argv"], list)
        # Any real machine has at least 1 GB of RAM.
        assert sys_block["ram_total"] > 1_000_000_000

        assert isinstance(data["devices"], list)
        if data["devices"]:
            dev = data["devices"][0]
            assert "name" in dev
            assert "type" in dev
            assert "vram_total" in dev
            assert dev["vram_total"] >= 0
            # index is null for CPU, int for CUDA
            assert dev["index"] is None or isinstance(dev["index"], int)

    def test_real_server_pretty_includes_version(self, capsys):
        from comfyui_cli.commands.info import run_info

        run_info(url=COMFY_URL, timeout=10.0, json_output=False)
        out = capsys.readouterr().out
        # Table should render something visible mentioning ComfyUI and GiB.
        assert "ComfyUI" in out
        assert "GiB" in out


# --- Tests: model list / find (live) ---------------------------------------


_KNOWN_MODEL_EXTS = (
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pt2",
    ".bin",
    ".pth",
    ".pkl",
    ".sft",
)


@skip_no_server
class TestModelListLive:
    def test_list_checkpoints_returns_list(self, capsys):
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="checkpoints", url=COMFY_URL, json_output=True
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "checkpoints" in data
        files = data["checkpoints"]
        assert isinstance(files, list)
        for f in files:
            assert isinstance(f, str)
            assert f.lower().endswith(_KNOWN_MODEL_EXTS), (
                f"unexpected extension: {f}"
            )

    def test_list_loras_returns_list(self, capsys):
        from comfyui_cli.commands.model_list import run_list

        run_list(type_name="loras", url=COMFY_URL, json_output=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "loras" in data
        files = data["loras"]
        assert isinstance(files, list)
        for f in files:
            assert isinstance(f, str)
            assert f.lower().endswith(_KNOWN_MODEL_EXTS), (
                f"unexpected extension: {f}"
            )

    def test_list_all_returns_counts_dict(self, capsys):
        from comfyui_cli.commands.model_list import run_list

        run_list(type_name=None, url=COMFY_URL, json_output=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        # Summary shape: expected model-type keys.
        for key in (
            "checkpoints",
            "loras",
            "vae",
            "controlnet",
            "upscale_models",
            "text_encoders",
            "embeddings",
        ):
            assert key in data, f"missing type {key} in summary"
            assert isinstance(data[key], int)
            assert data[key] >= 0

    def test_live_text_encoders_includes_v3_nodes(self, capsys):
        """On a live server, text_encoders union must include V3-COMBO-shaped files.

        Directly probes /object_info/TripleCLIPLoader. If the server emits the
        V3 COMBO shape (`["COMBO", {"options": [...]}]`), every option must
        appear in the `model list --type text_encoders` output. This regression-
        guards the silent-empty-result bug where a naive extractor read
        `spec[0]` as a list and got the string `"COMBO"` instead.
        """
        from comfyui_cli.commands.model_list import run_list

        # Discover what TripleCLIPLoader exposes on this live server, if anything.
        with httpx.Client(
            timeout=10.0, headers={"Origin": COMFY_URL}
        ) as c:
            r = c.get(f"{COMFY_URL}/object_info/TripleCLIPLoader")
        if r.status_code == 404:
            pytest.skip("Live server has no TripleCLIPLoader")
        r.raise_for_status()
        body = r.json()["TripleCLIPLoader"]
        spec = body["input"]["required"]["clip_name1"]

        # Determine expected filenames from whichever shape the server emitted.
        if isinstance(spec[0], str):
            # V3 COMBO shape
            expected = set(spec[1]["options"])
        else:
            expected = set(spec[0])

        if not expected:
            pytest.skip("TripleCLIPLoader on live server has no options")

        # Now run `model list --type text_encoders` and assert every
        # expected filename survives the union+extraction.
        run_list(type_name="text_encoders", url=COMFY_URL, json_output=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        listed = set(data["text_encoders"])
        missing = expected - listed
        assert not missing, (
            f"text_encoders missing V3-loader entries: {missing}; got {listed}"
        )

    def test_find_locates_a_known_file(self, capsys):
        """If any checkpoint or lora exists on the server, find() should locate it."""
        from comfyui_cli.commands.model_find import run_find
        from comfyui_cli.commands.model_list import run_list

        # Discover an existing file to search for.
        run_list(type_name="loras", url=COMFY_URL, json_output=True)
        out1 = capsys.readouterr().out
        loras = json.loads(out1).get("loras", [])

        run_list(type_name="checkpoints", url=COMFY_URL, json_output=True)
        out2 = capsys.readouterr().out
        ckpts = json.loads(out2).get("checkpoints", [])

        source_type = None
        seed_file: str | None = None
        if loras:
            source_type, seed_file = "loras", loras[0]
        elif ckpts:
            source_type, seed_file = "checkpoints", ckpts[0]
        else:
            pytest.skip("live server has no loras or checkpoints to search for")

        # Search for the first 4 chars as a prefix — that must match the file.
        needle = seed_file[:4]
        run_find(name=needle, url=COMFY_URL, json_output=True)
        out3 = capsys.readouterr().out
        data = json.loads(out3)
        assert source_type in data, (
            f"expected {source_type} in find results, got {data!r}"
        )
        assert seed_file in data[source_type]


# --- Tier 2: input upload ---------------------------------------------------

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@skip_no_server
class TestInputUploadLive:
    def test_upload_roundtrips_bytes(self, capsys):
        """Upload fixture, read back via /view, compare bytes.

        CLEANUP NOTE: ComfyUI has no delete endpoint. Uploaded files remain
        in the server's input/ directory until manually removed.
        """
        from comfyui_cli.commands.input_upload import run_upload

        fixture = FIXTURES / "tiny.png"
        original_bytes = fixture.read_bytes()

        run_upload(
            file=fixture,
            subfolder=None,
            overwrite=True,  # deterministic name on repeat runs
            url=COMFY_URL,
            json_output=False,
        )
        out = capsys.readouterr().out
        resp = json.loads(out)
        assert "name" in resp
        assert resp["type"] == "input"
        server_name = resp["name"]

        with httpx.Client(timeout=30.0, headers={"Origin": COMFY_URL}) as c:
            view = c.get(
                f"{COMFY_URL}/view",
                params={
                    "filename": server_name,
                    "subfolder": resp.get("subfolder", "") or "",
                    "type": "input",
                },
            )
        assert view.status_code == 200
        assert view.content == original_bytes


# --- Tier 2: output show (empty history) ------------------------------------


@skip_no_server
class TestOutputShowLive:
    def test_missing_prompt_id_exits_5(self):
        from comfyui_cli.commands.output_show import run_show
        from comfyui_cli.backend import ComfyNotFoundError

        with pytest.raises(ComfyNotFoundError) as ei:
            run_show(
                prompt_id="00000000-no-such-prompt-00000000",
                url=COMFY_URL,
                json_output=False,
            )
        assert ei.value.exit_code == 5


# --- Tier 2: workflow extract against real ComfyUI-generated images ---------
# Does NOT require a live server — only a prior ComfyUI output file on disk.


_COMFY_OUTPUT_DIR = Path(
    os.environ.get("COMFY_OUTPUT_DIR", r"E:\workspaces\tools\comfy\ComfyUI\output")
)


def _first_real_png() -> Path | None:
    """Return first non-empty PNG under the ComfyUI output dir, or None."""
    if not _COMFY_OUTPUT_DIR.is_dir():
        return None
    for p in sorted(_COMFY_OUTPUT_DIR.rglob("*.png")):
        if p.is_file() and p.stat().st_size > 0:
            return p
    return None


class TestWorkflowExtractLive:
    def test_extract_from_real_output_png(self, capsys):
        png = _first_real_png()
        if png is None:
            pytest.skip(
                f"No real ComfyUI output PNG found under {_COMFY_OUTPUT_DIR}"
            )
        from comfyui_cli.commands.workflow_extract import run_extract

        run_extract(
            image=png, ui=False, api=False, both=False, out_file=None
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        # Real workflow: dict keyed by string node ids; each has class_type.
        assert isinstance(data, dict) and data
        first = next(iter(data.values()))
        assert "class_type" in first


FIXTURES = Path(__file__).resolve().parent / "fixtures"


@skip_no_server
class TestQueueLive:
    def test_queue_list_returns_valid_shape(self, capsys):
        """GET /queue on the live server should parse to expected keys."""
        from comfyui_cli.commands.queue_list import run_list

        run_list(url=COMFY_URL, json_output=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "queue_running" in data
        assert "queue_pending" in data
        assert isinstance(data["queue_running"], list)
        assert isinstance(data["queue_pending"], list)

    def test_submit_invalid_workflow_returns_node_errors(self):
        """Submit a workflow referencing a nonexistent checkpoint.

        The real server returns 400 with node_errors — surfaces as
        ComfyValidationError (exit 3) via handle_http_errors.
        """
        from comfyui_cli.commands.queue_submit import run_submit
        from comfyui_cli.backend import ComfyValidationError

        workflow_path = FIXTURES / "minimal_workflow.json"
        assert workflow_path.exists(), f"Missing fixture: {workflow_path}"

        with pytest.raises(ComfyValidationError) as ei:
            run_submit(
                file=workflow_path,
                url=COMFY_URL,
                json_output=False,
            )
        assert ei.value.exit_code == 3
        assert len(ei.value.node_errors) >= 1

    def test_submit_ui_format_rejected_locally(self):
        """UI-format detection must reject before any HTTP call."""
        from comfyui_cli.commands.queue_submit import run_submit
        from comfyui_cli.backend import ComfyError

        ui_path = FIXTURES / "ui_workflow.json"
        assert ui_path.exists(), f"Missing fixture: {ui_path}"

        with pytest.raises(ComfyError) as ei:
            run_submit(file=ui_path, url=COMFY_URL)
        assert ei.value.exit_code == 3

    def test_free_unload_models_succeeds(self, capsys):
        """/free with --unload-models returns 200 even if it's a no-op."""
        from comfyui_cli.commands.queue_free import run_free

        run_free(url=COMFY_URL, unload_models=True, free_memory=False)
        out = capsys.readouterr().out
        assert "ok" in out.lower()

    def test_free_no_flags_refused(self):
        """No flags = exit 1 no-op warning; no HTTP request made."""
        from comfyui_cli.commands.queue_free import run_free
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_free(url=COMFY_URL, unload_models=False, free_memory=False)
        assert ei.value.exit_code == 1

    def test_clear_idempotent_on_live_server(self, capsys):
        """queue clear should succeed even when the queue is empty."""
        from comfyui_cli.commands.queue_clear import run_clear

        run_clear(url=COMFY_URL)
        out = capsys.readouterr().out
        assert "cleared" in out.lower()
        assert "pending" in out.lower()

    def test_status_with_unknown_id_exits_5(self):
        """history/<unknown> returns {} on the real server → ComfyNotFoundError."""
        from comfyui_cli.commands.queue_status import run_status
        from comfyui_cli.backend import ComfyNotFoundError

        bogus = "00000000-0000-0000-0000-000000000000-nope"
        with pytest.raises(ComfyNotFoundError) as ei:
            run_status(prompt_id=bogus, url=COMFY_URL, json_output=False)
        assert ei.value.exit_code == 5

    def test_cancel_unknown_id_is_idempotent(self, capsys):
        """cancel against an unknown id: server accepts both calls as no-ops."""
        from comfyui_cli.commands.queue_cancel import run_cancel

        bogus = "00000000-0000-0000-0000-000000000000-nope"
        run_cancel(prompt_id=bogus, url=COMFY_URL)
        out = capsys.readouterr().out
        assert "cancelled" in out.lower() or bogus in out


# --- Tier 2: workflow run against the live server --------------------------
# The live install has no checkpoints, so we can't run a real SD1.5 workflow.
# Instead we prove the compose path by submitting the minimal invalid workflow
# and asserting node_errors are surfaced as exit 3.


@skip_no_server
class TestWorkflowRunLive:
    def test_invalid_workflow_surfaces_node_errors(self):
        """Live server rejects nonexistent checkpoint with node_errors (exit 3)."""
        from comfyui_cli.commands.workflow_run import run_run
        from comfyui_cli.backend import ComfyValidationError

        workflow_path = FIXTURES / "minimal_workflow.json"
        assert workflow_path.exists(), f"Missing fixture: {workflow_path}"

        with pytest.raises(ComfyValidationError) as ei:
            run_run(
                file=workflow_path,
                url=COMFY_URL,
                live=False,
                timeout=10.0,
            )
        assert ei.value.exit_code == 3
        assert len(ei.value.node_errors) >= 1

    def test_ui_format_rejected_before_http(self):
        """UI-format detection must reject before any server interaction."""
        from comfyui_cli.commands.workflow_run import run_run
        from comfyui_cli.backend import ComfyError

        ui_path = FIXTURES / "ui_workflow.json"
        assert ui_path.exists(), f"Missing fixture: {ui_path}"

        with pytest.raises(ComfyError) as ei:
            run_run(
                file=ui_path,
                url=COMFY_URL,
                live=False,
                timeout=10.0,
            )
        assert ei.value.exit_code == 3
