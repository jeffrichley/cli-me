"""Tier 1 tests for the ComfyUI cli-me skill.

All HTTP calls are mocked via pytest-httpx. Workflow tests operate on
on-disk JSON fixtures and in-memory PNG/WebP images via Pillow, so no
live ComfyUI process is required. Tests must be deterministic.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

# Make `scripts/` importable so `from comfyui_cli...` resolves.
scripts_dir = (
    Path(__file__).resolve().parent.parent.parent
    / "skill-repo"
    / "comfyui"
    / "scripts"
)
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# --- Realistic /system_stats fixtures ---------------------------------------


def _gpu_stats() -> dict:
    """A realistic /system_stats payload from a GPU host."""
    return {
        "system": {
            "os": "win32",
            "ram_total": 68499132416,
            "ram_free": 38207627264,
            "comfyui_version": "0.19.0",
            "required_frontend_version": "1.42.10",
            "installed_templates_version": "0.9.47",
            "required_templates_version": "0.9.47",
            "python_version": "3.12.10 (main, May 30 2025, 05:39:07) [MSC v.1943 64 bit (AMD64)]",
            "pytorch_version": "2.11.0+cu130",
            "embedded_python": False,
            "argv": ["main.py", "--listen", "127.0.0.1", "--port", "8188"],
        },
        "devices": [
            {
                "name": "cuda:0 NVIDIA GeForce RTX 4060 Ti : cudaMallocAsync",
                "type": "cuda",
                "index": 0,
                "vram_total": 17175150592,
                "vram_free": 15962472448,
                "torch_vram_total": 0,
                "torch_vram_free": 0,
            }
        ],
    }


def _cpu_stats() -> dict:
    """A /system_stats payload from a CPU-only host (null index)."""
    return {
        "system": {
            "os": "linux",
            "ram_total": 34359738368,
            "ram_free": 16384000000,
            "comfyui_version": "0.19.0",
            "required_frontend_version": "1.42.10",
            "installed_templates_version": "0.9.47",
            "required_templates_version": "0.9.47",
            "python_version": "3.12.0",
            "pytorch_version": "2.11.0",
            "embedded_python": False,
            "argv": ["main.py", "--cpu"],
        },
        "devices": [
            {
                "name": "cpu",
                "type": "cpu",
                "index": None,
                "vram_total": 34359738368,
                "vram_free": 16384000000,
                "torch_vram_total": 0,
                "torch_vram_free": 0,
            }
        ],
    }


def _minimal_stats() -> dict:
    """Minimal but complete /system_stats — for URL-precedence tests."""
    return {
        "system": {
            "os": "linux",
            "ram_total": 1073741824,
            "ram_free": 536870912,
            "comfyui_version": "0.19.0",
            "python_version": "3.12.0",
            "pytorch_version": "2.11.0",
            "embedded_python": False,
            "argv": [],
        },
        "devices": [],
    }


# --- Tests: server ping -----------------------------------------------------


class TestPing:
    def test_returns_ok_on_200(self, httpx_mock: HTTPXMock, capsys):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=_gpu_stats(),
        )
        from comfyui_cli.commands.ping import run_ping

        run_ping(url="http://127.0.0.1:8188", timeout=5.0)
        captured = capsys.readouterr()
        assert "ok" in captured.out.lower()
        assert "0.19.0" in captured.out

    def test_output_includes_device_info(self, httpx_mock: HTTPXMock, capsys):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=_gpu_stats(),
        )
        from comfyui_cli.commands.ping import run_ping

        run_ping(url="http://127.0.0.1:8188", timeout=5.0)
        out = capsys.readouterr().out
        # Device type and some piece of the name (vendor-string fragment)
        assert "cuda" in out.lower()
        assert "4060 Ti" in out

    def test_sends_origin_header(self, httpx_mock: HTTPXMock):
        """Critical: origin-guard gotcha — Origin must match base URL."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=_gpu_stats(),
        )
        from comfyui_cli.commands.ping import run_ping

        run_ping(url="http://127.0.0.1:8188", timeout=5.0)
        req = httpx_mock.get_request()
        assert req is not None
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"

    def test_strips_trailing_slash_from_url(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=_gpu_stats(),
        )
        from comfyui_cli.commands.ping import run_ping

        run_ping(url="http://127.0.0.1:8188/", timeout=5.0)
        req = httpx_mock.get_request()
        assert req is not None
        # URL should hit /system_stats, not //system_stats
        assert str(req.url) == "http://127.0.0.1:8188/system_stats"

    def test_exits_2_on_connection_refused(self):
        """Port 1 will refuse — real network error, no mock needed."""
        from comfyui_cli.commands.ping import run_ping
        from comfyui_cli.backend import ComfyConnectionError

        with pytest.raises(ComfyConnectionError) as ei:
            run_ping(url="http://127.0.0.1:1", timeout=2.0)
        assert ei.value.exit_code == 2

    def test_exits_2_on_403(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            status_code=403,
            text="",
        )
        from comfyui_cli.commands.ping import run_ping
        from comfyui_cli.backend import ComfyOriginError

        with pytest.raises(ComfyOriginError) as ei:
            run_ping(url="http://127.0.0.1:8188", timeout=5.0)
        assert ei.value.exit_code == 2

    def test_exits_1_on_500(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            status_code=500,
            text="internal error",
        )
        from comfyui_cli.commands.ping import run_ping
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_ping(url="http://127.0.0.1:8188", timeout=5.0)
        assert ei.value.exit_code == 1

    def test_ping_read_timeout_raises_connection(self, httpx_mock: HTTPXMock):
        """ReadTimeout must not escape as a raw traceback."""
        import httpx

        httpx_mock.add_exception(httpx.ReadTimeout("timed out"))
        from comfyui_cli.commands.ping import run_ping
        from comfyui_cli.backend import ComfyConnectionError

        with pytest.raises(ComfyConnectionError) as ei:
            run_ping(url="http://127.0.0.1:8188", timeout=5.0)
        assert "timed out" in str(ei.value).lower()
        assert ei.value.exit_code == 2

    def test_ping_non_json_200_raises_clearly(self, httpx_mock: HTTPXMock):
        """A reverse proxy returning HTML with 200 must surface a clear error."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            status_code=200,
            text="<html>error</html>",
            headers={"content-type": "text/html"},
        )
        from comfyui_cli.commands.ping import run_ping
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_ping(url="http://127.0.0.1:8188", timeout=5.0)
        msg = str(ei.value).lower()
        assert "non-json" in msg or "reverse proxy" in msg


# --- Tests: URL precedence (flag > env > default) ---------------------------


class TestUrlPrecedence:
    def test_url_flag_overrides_env(self, monkeypatch, httpx_mock: HTTPXMock):
        monkeypatch.setenv("COMFY_URL", "http://env-host:9999")
        httpx_mock.add_response(
            url="http://flag-host:8888/system_stats",
            json=_minimal_stats(),
        )
        from comfyui_cli.commands.ping import run_ping

        run_ping(url="http://flag-host:8888", timeout=5.0)
        req = httpx_mock.get_request()
        assert req is not None
        assert "flag-host" in str(req.url)

    def test_env_used_when_no_flag(self, monkeypatch, httpx_mock: HTTPXMock):
        monkeypatch.setenv("COMFY_URL", "http://env-host:7777")
        httpx_mock.add_response(
            url="http://env-host:7777/system_stats",
            json=_minimal_stats(),
        )
        from comfyui_cli.commands.ping import run_ping

        run_ping(url=None, timeout=5.0)
        req = httpx_mock.get_request()
        assert req is not None
        assert "env-host" in str(req.url)

    def test_default_url_when_nothing_set(
        self, monkeypatch, httpx_mock: HTTPXMock
    ):
        monkeypatch.delenv("COMFY_URL", raising=False)
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=_minimal_stats(),
        )
        from comfyui_cli.commands.ping import run_ping

        run_ping(url=None, timeout=5.0)
        req = httpx_mock.get_request()
        assert req is not None
        assert "127.0.0.1:8188" in str(req.url)


# --- Tests: server info -----------------------------------------------------


class TestInfo:
    def test_pretty_table_includes_version_and_device(
        self, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=_gpu_stats(),
        )
        from comfyui_cli.commands.info import run_info

        run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=False)
        out = capsys.readouterr().out
        assert "0.19.0" in out
        assert "2.11.0+cu130" in out
        assert "4060 Ti" in out

    def test_pretty_table_formats_ram_as_gib(
        self, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=_gpu_stats(),
        )
        from comfyui_cli.commands.info import run_info

        run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=False)
        out = capsys.readouterr().out
        # 68499132416 bytes / (1024**3) ≈ 63.79 → "63.8 GiB"
        assert "63.8 GiB" in out
        # 38207627264 bytes / (1024**3) ≈ 35.58 → "35.6 GiB"
        assert "35.6 GiB" in out
        # 17175150592 bytes / (1024**3) ≈ 16.00 → "16.0 GiB"
        assert "16.0 GiB" in out
        # 15962472448 bytes / (1024**3) ≈ 14.87 → "14.9 GiB"
        assert "14.9 GiB" in out

    def test_json_output_is_raw_bytes(self, httpx_mock: HTTPXMock, capsys):
        """--json must emit the server's exact bytes, not a re-serialized dict."""
        expected_body = (
            '{"system":{"os":"linux","ram_total":1073741824,"ram_free":536870912,'
            '"comfyui_version":"0.19.0","python_version":"3.12.0",'
            '"pytorch_version":"2.11.0","embedded_python":false,"argv":[]},'
            '"devices":[]}'
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            text=expected_body,
            headers={"content-type": "application/json"},
        )
        from comfyui_cli.commands.info import run_info

        run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=True)
        out = capsys.readouterr().out
        # Byte-equal — no re-serialization (no pretty indent, no key reorder).
        assert out == expected_body or out == expected_body + "\n"

    def test_json_output_parses_to_server_json(self, httpx_mock: HTTPXMock, capsys):
        """Sanity: whatever bytes we wrote still parse back to the original dict."""
        response_json = _gpu_stats()
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=response_json,
        )
        from comfyui_cli.commands.info import run_info

        run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=True)
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed == response_json

    def test_cpu_device_with_null_index(self, httpx_mock: HTTPXMock, capsys):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=_cpu_stats(),
        )
        from comfyui_cli.commands.info import run_info

        run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=False)
        out = capsys.readouterr().out
        assert "cpu" in out.lower()
        # Should not crash with TypeError when index is None

    def test_sends_origin_header(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            json=_gpu_stats(),
        )
        from comfyui_cli.commands.info import run_info

        run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=True)
        req = httpx_mock.get_request()
        assert req is not None
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"

    def test_exits_2_on_connection_refused(self):
        from comfyui_cli.commands.info import run_info
        from comfyui_cli.backend import ComfyConnectionError

        with pytest.raises(ComfyConnectionError) as ei:
            run_info(url="http://127.0.0.1:1", timeout=2.0, json_output=False)
        assert ei.value.exit_code == 2

    def test_exits_2_on_403(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            status_code=403,
            text="",
        )
        from comfyui_cli.commands.info import run_info
        from comfyui_cli.backend import ComfyOriginError

        with pytest.raises(ComfyOriginError):
            run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=False)

    def test_info_404_raises_not_found(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            status_code=404,
            text="Not Found",
        )
        from comfyui_cli.commands.info import run_info
        from comfyui_cli.backend import ComfyNotFoundError

        with pytest.raises(ComfyNotFoundError) as ei:
            run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=False)
        assert ei.value.exit_code == 5

    def test_info_500_raises_generic(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            status_code=500,
            text="boom",
        )
        from comfyui_cli.commands.info import run_info
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=False)
        assert ei.value.exit_code == 1

    def test_info_read_timeout_raises_connection(self, httpx_mock: HTTPXMock):
        """ReadTimeout must not escape as a raw traceback."""
        import httpx

        httpx_mock.add_exception(httpx.ReadTimeout("timed out"))
        from comfyui_cli.commands.info import run_info
        from comfyui_cli.backend import ComfyConnectionError

        with pytest.raises(ComfyConnectionError) as ei:
            run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=False)
        assert "timed out" in str(ei.value).lower()
        assert ei.value.exit_code == 2

    def test_info_non_json_200_raises_clearly(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/system_stats",
            status_code=200,
            text="<html>error</html>",
            headers={"content-type": "text/html"},
        )
        from comfyui_cli.commands.info import run_info
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_info(url="http://127.0.0.1:8188", timeout=5.0, json_output=False)
        msg = str(ei.value).lower()
        assert "non-json" in msg or "reverse proxy" in msg


# --- Fixtures: /object_info shape ------------------------------------------


def _loader_body(node_class: str, param: str, files: list[str]) -> dict:
    """Build an /object_info/<node_class> response with a dropdown enum."""
    return {
        node_class: {
            "input": {
                "required": {
                    param: [files, {"tooltip": "x"}],
                }
            },
            "input_order": {"required": [param]},
            "output": ["MODEL"],
            "output_is_list": [False],
            "output_name": ["MODEL"],
            "name": node_class,
            "display_name": node_class,
            "description": "",
            "python_module": "nodes",
            "category": "loaders",
            "output_node": False,
        }
    }


# --- Tests: model list ------------------------------------------------------


class TestModelList:
    def test_list_checkpoints_hits_right_endpoint(
        self, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CheckpointLoaderSimple",
            json=_loader_body(
                "CheckpointLoaderSimple",
                "ckpt_name",
                ["sd_xl_base_1.0.safetensors", "flux1-dev.safetensors"],
            ),
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="checkpoints",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data == {
            "checkpoints": [
                "sd_xl_base_1.0.safetensors",
                "flux1-dev.safetensors",
            ]
        }
        req = httpx_mock.get_request()
        assert req is not None
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"
        assert "/object_info/CheckpointLoaderSimple" in str(req.url)

    def test_list_text_encoders_unions_three_nodes(
        self, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CLIPLoader",
            json=_loader_body(
                "CLIPLoader", "clip_name", ["clip_a.safetensors", "t5.safetensors"]
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/DualCLIPLoader",
            json={
                "DualCLIPLoader": {
                    "input": {
                        "required": {
                            "clip_name1": [
                                ["clip_a.safetensors", "clip_g.safetensors"],
                                {},
                            ],
                            "clip_name2": [
                                ["t5.safetensors", "clip_l.safetensors"],
                                {},
                            ],
                        }
                    },
                    "input_order": {"required": ["clip_name1", "clip_name2"]},
                    "output": ["CLIP"],
                    "output_is_list": [False],
                    "output_name": ["CLIP"],
                    "name": "DualCLIPLoader",
                    "display_name": "DualCLIPLoader",
                    "description": "",
                    "python_module": "nodes",
                    "category": "loaders",
                    "output_node": False,
                }
            },
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/TripleCLIPLoader",
            json={
                "TripleCLIPLoader": {
                    "input": {
                        "required": {
                            "clip_name1": [["clip_a.safetensors"], {}],
                            "clip_name2": [["clip_g.safetensors"], {}],
                            "clip_name3": [["t5.safetensors", "pile.safetensors"], {}],
                        }
                    },
                    "input_order": {
                        "required": ["clip_name1", "clip_name2", "clip_name3"]
                    },
                    "output": ["CLIP"],
                    "output_is_list": [False],
                    "output_name": ["CLIP"],
                    "name": "TripleCLIPLoader",
                    "display_name": "TripleCLIPLoader",
                    "description": "",
                    "python_module": "nodes",
                    "category": "loaders",
                    "output_node": False,
                }
            },
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="text_encoders",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        # Union of all three — 5 unique filenames
        assert set(data["text_encoders"]) == {
            "clip_a.safetensors",
            "clip_g.safetensors",
            "clip_l.safetensors",
            "t5.safetensors",
            "pile.safetensors",
        }

    def test_list_without_type_returns_counts(
        self, httpx_mock: HTTPXMock, capsys
    ):
        # Stock loaders the summary queries
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CheckpointLoaderSimple",
            json=_loader_body(
                "CheckpointLoaderSimple",
                "ckpt_name",
                ["a.safetensors", "b.safetensors"],
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/LoraLoader",
            json=_loader_body("LoraLoader", "lora_name", ["l1.safetensors"]),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/VAELoader",
            json=_loader_body("VAELoader", "vae_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/ControlNetLoader",
            json=_loader_body("ControlNetLoader", "control_net_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/UpscaleModelLoader",
            json=_loader_body("UpscaleModelLoader", "model_name", ["u.pt"]),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CLIPLoader",
            json=_loader_body(
                "CLIPLoader", "clip_name", ["c1.safetensors"]
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/DualCLIPLoader",
            json={
                "DualCLIPLoader": {
                    "input": {
                        "required": {
                            "clip_name1": [["c1.safetensors"], {}],
                            "clip_name2": [["c2.safetensors"], {}],
                        }
                    },
                    "input_order": {"required": ["clip_name1", "clip_name2"]},
                    "output": ["CLIP"],
                    "output_is_list": [False],
                    "output_name": ["CLIP"],
                    "name": "DualCLIPLoader",
                    "display_name": "DualCLIPLoader",
                    "description": "",
                    "python_module": "nodes",
                    "category": "loaders",
                    "output_node": False,
                }
            },
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/TripleCLIPLoader",
            status_code=404,
            text="not found",
        )
        # Expanded loader set: diffusion_models, clip_vision, style_models,
        # hypernetworks, gligen, photomaker
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/UNETLoader",
            json=_loader_body(
                "UNETLoader", "unet_name", ["flux1-dev.safetensors"]
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/StyleModelLoader",
            json=_loader_body("StyleModelLoader", "style_model_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CLIPVisionLoader",
            json=_loader_body(
                "CLIPVisionLoader", "clip_name", ["clip_vision_h.safetensors"]
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/HypernetworkLoader",
            json=_loader_body("HypernetworkLoader", "hypernetwork_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/GLIGENLoader",
            json=_loader_body("GLIGENLoader", "gligen_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/PhotoMakerLoader",
            status_code=404,
            text="not found",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/embeddings",
            json=["emb1.pt"],
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(type_name=None, url="http://127.0.0.1:8188", json_output=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        # Counts shape: dict keyed by type
        assert data["checkpoints"] == 2
        assert data["loras"] == 1
        assert data["vae"] == 0
        assert data["upscale_models"] == 1
        assert data["embeddings"] == 1
        # text_encoders union: c1, c2 → 2
        assert data["text_encoders"] == 2
        # New types added in the TYPE_TO_NODES expansion
        assert data["diffusion_models"] == 1
        assert data["clip_vision"] == 1
        assert data["style_models"] == 0
        assert data["hypernetworks"] == 0
        assert data["gligen"] == 0
        assert data["photomaker"] == 0  # 404 → empty

    def test_list_embeddings_uses_special_endpoint(
        self, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/embeddings",
            json=["bad_hands.pt", "easynegative.safetensors"],
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="embeddings",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data == {
            "embeddings": ["bad_hands.pt", "easynegative.safetensors"]
        }
        req = httpx_mock.get_request()
        assert req is not None
        assert str(req.url).endswith("/embeddings")

    def test_list_unknown_type_errors(self):
        from comfyui_cli.commands.model_list import run_list
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_list(type_name="foobar", url="http://127.0.0.1:8188", json_output=False)
        assert ei.value.exit_code == 3

    def test_is_enum_rejects_typed_socket(self):
        from comfyui_cli.commands.model_list import is_enum

        assert is_enum(["LATENT"]) is False
        assert is_enum(["MODEL"]) is False

    def test_list_diffusion_models_uses_unet_loader(
        self, httpx_mock: HTTPXMock, capsys
    ):
        """--type diffusion_models must hit /object_info/UNETLoader."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/UNETLoader",
            json=_loader_body(
                "UNETLoader",
                "unet_name",
                [
                    "flux1-schnell-fp8.safetensors",
                    "wan2.2_t2v_high_noise.safetensors",
                ],
            ),
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="diffusion_models",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data == {
            "diffusion_models": [
                "flux1-schnell-fp8.safetensors",
                "wan2.2_t2v_high_noise.safetensors",
            ]
        }
        req = httpx_mock.get_request()
        assert req is not None
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"
        assert "/object_info/UNETLoader" in str(req.url)

    def test_list_clip_vision_uses_clipvision_loader(
        self, httpx_mock: HTTPXMock, capsys
    ):
        """--type clip_vision must hit /object_info/CLIPVisionLoader (NOT CLIPLoader)."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CLIPVisionLoader",
            json=_loader_body(
                "CLIPVisionLoader",
                "clip_name",
                ["clip_vision_h.safetensors", "clip_vision_g.safetensors"],
            ),
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="clip_vision",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["clip_vision"] == [
            "clip_vision_h.safetensors",
            "clip_vision_g.safetensors",
        ]
        req = httpx_mock.get_request()
        assert req is not None
        assert "/object_info/CLIPVisionLoader" in str(req.url)

    def test_list_style_models_uses_stylemodel_loader(
        self, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/StyleModelLoader",
            json=_loader_body(
                "StyleModelLoader", "style_model_name", ["flux-redux.safetensors"]
            ),
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="style_models",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data == {"style_models": ["flux-redux.safetensors"]}

    def test_is_enum_additional_cases(self):
        """Additional is_enum edge cases — file-list vs typed-socket."""
        from comfyui_cli.commands.model_list import is_enum

        assert is_enum(["CLIP"]) is False
        assert is_enum(["sd.safetensors", "flux.safetensors"]) is True
        # Single filename entry — not uppercase-type, still an enum
        assert is_enum(["sd.safetensors"]) is True
        # Empty list — no enum
        assert is_enum([]) is False
        # Non-list
        assert is_enum("INT") is False

    def test_list_json_output_shape(self, httpx_mock: HTTPXMock, capsys):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CheckpointLoaderSimple",
            json=_loader_body(
                "CheckpointLoaderSimple",
                "ckpt_name",
                ["a.safetensors", "b.safetensors"],
            ),
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="checkpoints",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data == {
            "checkpoints": ["a.safetensors", "b.safetensors"]
        }

    def test_list_extracts_v3_combo_shape(
        self, httpx_mock: HTTPXMock, capsys
    ):
        """V3 nodes emit ['COMBO', {'options': [...], ...}]; extractor must read options."""
        # Stub the non-V3 members of the text_encoders union as empty so only
        # the V3 TripleCLIPLoader contributes.
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CLIPLoader",
            json=_loader_body("CLIPLoader", "clip_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/DualCLIPLoader",
            status_code=404,
            text="not found",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/TripleCLIPLoader",
            json={
                "TripleCLIPLoader": {
                    "input": {
                        "required": {
                            "clip_name1": [
                                "COMBO",
                                {
                                    "multiselect": False,
                                    "options": [
                                        "clip_l.safetensors",
                                        "t5xxl_fp8_e4m3fn.safetensors",
                                        "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                                    ],
                                },
                            ],
                            "clip_name2": [
                                "COMBO",
                                {
                                    "multiselect": False,
                                    "options": [
                                        "clip_l.safetensors",
                                        "t5xxl_fp8_e4m3fn.safetensors",
                                        "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                                    ],
                                },
                            ],
                            "clip_name3": [
                                "COMBO",
                                {
                                    "multiselect": False,
                                    "options": [
                                        "clip_l.safetensors",
                                        "t5xxl_fp8_e4m3fn.safetensors",
                                        "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                                    ],
                                },
                            ],
                        }
                    },
                    "input_order": {
                        "required": ["clip_name1", "clip_name2", "clip_name3"]
                    },
                    "output": ["CLIP"],
                    "output_is_list": [False],
                    "output_name": ["CLIP"],
                    "name": "TripleCLIPLoader",
                    "display_name": "TripleCLIPLoader",
                    "description": "",
                    "python_module": "comfy_extras.nodes_sd3",
                    "category": "advanced/loaders",
                    "output_node": False,
                }
            },
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="text_encoders",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert set(data["text_encoders"]) == {
            "clip_l.safetensors",
            "t5xxl_fp8_e4m3fn.safetensors",
            "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        }

    def test_list_handles_mixed_v3_and_legacy_in_union(
        self, httpx_mock: HTTPXMock, capsys
    ):
        """Mixed loader shapes in one union must contribute files from BOTH."""
        # Legacy CLIPLoader exposes unique_legacy.safetensors; V3 TripleCLIPLoader
        # exposes unique_v3.safetensors. The union must contain both.
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CLIPLoader",
            json=_loader_body(
                "CLIPLoader",
                "clip_name",
                ["shared.safetensors", "unique_legacy.safetensors"],
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/DualCLIPLoader",
            status_code=404,
            text="not found",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/TripleCLIPLoader",
            json={
                "TripleCLIPLoader": {
                    "input": {
                        "required": {
                            "clip_name1": [
                                "COMBO",
                                {
                                    "options": [
                                        "shared.safetensors",
                                        "unique_v3.safetensors",
                                    ],
                                },
                            ],
                            "clip_name2": [
                                "COMBO",
                                {
                                    "options": [
                                        "shared.safetensors",
                                        "unique_v3.safetensors",
                                    ],
                                },
                            ],
                            "clip_name3": [
                                "COMBO",
                                {
                                    "options": [
                                        "shared.safetensors",
                                        "unique_v3.safetensors",
                                    ],
                                },
                            ],
                        }
                    },
                    "input_order": {
                        "required": ["clip_name1", "clip_name2", "clip_name3"]
                    },
                    "output": ["CLIP"],
                    "output_is_list": [False],
                    "output_name": ["CLIP"],
                    "name": "TripleCLIPLoader",
                    "display_name": "TripleCLIPLoader",
                    "description": "",
                    "python_module": "comfy_extras.nodes_sd3",
                    "category": "advanced/loaders",
                    "output_node": False,
                }
            },
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="text_encoders",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert set(data["text_encoders"]) == {
            "shared.safetensors",
            "unique_legacy.safetensors",
            "unique_v3.safetensors",
        }

    def test_all_model_endpoints_send_origin_header(
        self, httpx_mock: HTTPXMock, capsys
    ):
        """Every loader GET + /embeddings must carry the Origin header.

        Covers the text_encoders path (legacy + V3) and embeddings special-case.
        """
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CLIPLoader",
            json=_loader_body(
                "CLIPLoader", "clip_name", ["clip_l.safetensors"]
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/DualCLIPLoader",
            status_code=404,
            text="not found",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/TripleCLIPLoader",
            json={
                "TripleCLIPLoader": {
                    "input": {
                        "required": {
                            "clip_name1": [
                                "COMBO",
                                {"options": ["t5xxl.safetensors"]},
                            ],
                            "clip_name2": [
                                "COMBO",
                                {"options": ["t5xxl.safetensors"]},
                            ],
                            "clip_name3": [
                                "COMBO",
                                {"options": ["t5xxl.safetensors"]},
                            ],
                        }
                    },
                    "input_order": {
                        "required": ["clip_name1", "clip_name2", "clip_name3"]
                    },
                    "output": ["CLIP"],
                    "output_is_list": [False],
                    "output_name": ["CLIP"],
                    "name": "TripleCLIPLoader",
                    "display_name": "TripleCLIPLoader",
                    "description": "",
                    "python_module": "comfy_extras.nodes_sd3",
                    "category": "advanced/loaders",
                    "output_node": False,
                }
            },
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/embeddings",
            json=["easynegative.pt"],
        )
        from comfyui_cli.commands.model_list import run_list

        # text_encoders path -> hits CLIPLoader, DualCLIPLoader, TripleCLIPLoader
        run_list(
            type_name="text_encoders",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        capsys.readouterr()
        # embeddings special path
        run_list(
            type_name="embeddings",
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        capsys.readouterr()

        requests = httpx_mock.get_requests()
        # Must have hit CLIPLoader, DualCLIPLoader (even though 404), TripleCLIPLoader,
        # and /embeddings - every request carries Origin.
        paths_seen = {str(r.url).rsplit("/", 1)[-1] for r in requests}
        assert "CLIPLoader" in paths_seen
        assert "DualCLIPLoader" in paths_seen
        assert "TripleCLIPLoader" in paths_seen
        assert "embeddings" in paths_seen
        for req in requests:
            assert req.headers.get("Origin") == "http://127.0.0.1:8188", (
                f"Missing Origin on {req.url}"
            )

    def test_model_list_url_flag_overrides_env(
        self, httpx_mock: HTTPXMock, capsys, monkeypatch
    ):
        """--url flag must beat COMFY_URL env var."""
        monkeypatch.setenv("COMFY_URL", "http://env-host:9999")
        httpx_mock.add_response(
            url="http://flag-host:8188/object_info/CheckpointLoaderSimple",
            json=_loader_body(
                "CheckpointLoaderSimple",
                "ckpt_name",
                ["from_flag.safetensors"],
            ),
        )
        from comfyui_cli.commands.model_list import run_list

        run_list(
            type_name="checkpoints",
            url="http://flag-host:8188",
            json_output=True,
        )
        req = httpx_mock.get_request()
        assert req is not None
        assert str(req.url).startswith("http://flag-host:8188")
        # Origin reflects the flag URL, not the env.
        assert req.headers.get("Origin") == "http://flag-host:8188"


# --- Tests: model find ------------------------------------------------------


class TestModelFind:
    def _mock_all_loaders(self, httpx_mock: HTTPXMock):
        """Populate the full set of loader endpoints."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CheckpointLoaderSimple",
            json=_loader_body(
                "CheckpointLoaderSimple",
                "ckpt_name",
                ["sd_xl_base_1.0.safetensors", "flux1-dev.safetensors"],
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/LoraLoader",
            json=_loader_body(
                "LoraLoader",
                "lora_name",
                ["xl_lora.safetensors", "mylora.safetensors"],
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/VAELoader",
            json=_loader_body("VAELoader", "vae_name", ["sdxl_vae.safetensors"]),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/ControlNetLoader",
            json=_loader_body("ControlNetLoader", "control_net_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/UpscaleModelLoader",
            json=_loader_body("UpscaleModelLoader", "model_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CLIPLoader",
            json=_loader_body("CLIPLoader", "clip_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/DualCLIPLoader",
            status_code=404,
            text="not found",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/TripleCLIPLoader",
            status_code=404,
            text="not found",
        )
        # Expanded model-type coverage — empty/404 here is fine for the find tests
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/UNETLoader",
            json=_loader_body(
                "UNETLoader", "unet_name", ["flux1-schnell-fp8.safetensors"]
            ),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/StyleModelLoader",
            json=_loader_body("StyleModelLoader", "style_model_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/CLIPVisionLoader",
            json=_loader_body("CLIPVisionLoader", "clip_name", []),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/HypernetworkLoader",
            status_code=404,
            text="not found",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/GLIGENLoader",
            status_code=404,
            text="not found",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/object_info/PhotoMakerLoader",
            status_code=404,
            text="not found",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/embeddings",
            json=[],
        )

    def test_find_matches_case_insensitive(
        self, httpx_mock: HTTPXMock, capsys
    ):
        self._mock_all_loaders(httpx_mock)
        from comfyui_cli.commands.model_find import run_find

        run_find(name="XL", url="http://127.0.0.1:8188", json_output=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        # "XL" matches sd_xl_base_1.0, xl_lora, sdxl_vae (all case-insensitive)
        assert "checkpoints" in data
        assert "sd_xl_base_1.0.safetensors" in data["checkpoints"]
        assert "loras" in data
        assert "xl_lora.safetensors" in data["loras"]
        assert "vae" in data
        assert "sdxl_vae.safetensors" in data["vae"]

    def test_find_no_matches_prints_no_matches(
        self, httpx_mock: HTTPXMock, capsys
    ):
        self._mock_all_loaders(httpx_mock)
        from comfyui_cli.commands.model_find import run_find

        # A string that shouldn't match any of the fixtures
        run_find(
            name="zzzzzzzzzz_no_match_token",
            url="http://127.0.0.1:8188",
            json_output=False,
        )
        captured = capsys.readouterr()
        combined = (captured.out + captured.err).lower()
        assert "no matches" in combined

    def test_find_sends_origin_header_on_every_request(
        self, httpx_mock: HTTPXMock, capsys
    ):
        """model find spans every loader endpoint + /embeddings; all must carry Origin."""
        self._mock_all_loaders(httpx_mock)
        from comfyui_cli.commands.model_find import run_find

        run_find(name="flux", url="http://127.0.0.1:8188", json_output=True)
        capsys.readouterr()

        requests = httpx_mock.get_requests()
        assert len(requests) >= 3  # at least checkpoints, loras, something else
        for req in requests:
            assert req.headers.get("Origin") == "http://127.0.0.1:8188", (
                f"Missing Origin on {req.url}"
            )

    def test_model_find_uses_default_url(
        self, httpx_mock: HTTPXMock, capsys, monkeypatch
    ):
        """With no --url flag and no COMFY_URL env, falls back to 127.0.0.1:8188."""
        monkeypatch.delenv("COMFY_URL", raising=False)
        self._mock_all_loaders(httpx_mock)
        from comfyui_cli.commands.model_find import run_find

        run_find(name="flux", url=None, json_output=True)
        capsys.readouterr()

        requests = httpx_mock.get_requests()
        assert requests
        # All requests routed to the default base URL.
        for req in requests:
            assert str(req.url).startswith("http://127.0.0.1:8188"), (
                f"Expected default base, got {req.url}"
            )


# --- Tests: input upload ----------------------------------------------------


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestInputUpload:
    def test_sends_multipart_with_correct_fields(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/upload/image",
            method="POST",
            json={"name": "tiny.png", "subfolder": "refs", "type": "input"},
        )
        from comfyui_cli.commands.input_upload import run_upload

        run_upload(
            file=FIXTURES / "tiny.png",
            subfolder="refs",
            overwrite=False,
            url="http://127.0.0.1:8188",
            json_output=False,
        )
        req = httpx_mock.get_request()
        assert req is not None
        body = req.read()
        assert b'name="image"' in body
        assert b'name="type"' in body
        assert b"input" in body
        assert b'name="subfolder"' in body
        assert b"refs" in body
        assert b'name="overwrite"' in body
        assert b"false" in body

    def test_origin_header_set(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/upload/image",
            method="POST",
            json={"name": "tiny.png", "subfolder": "", "type": "input"},
        )
        from comfyui_cli.commands.input_upload import run_upload

        run_upload(
            file=FIXTURES / "tiny.png",
            subfolder=None,
            overwrite=False,
            url="http://127.0.0.1:8188",
            json_output=False,
        )
        req = httpx_mock.get_request()
        assert req is not None
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"

    def test_returns_server_assigned_name(self, httpx_mock: HTTPXMock, capsys):
        """Wiki gotcha: server may rename on collision; return server `name`."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/upload/image",
            method="POST",
            json={"name": "tiny (1).png", "subfolder": "", "type": "input"},
        )
        from comfyui_cli.commands.input_upload import run_upload

        run_upload(
            file=FIXTURES / "tiny.png",
            subfolder=None,
            overwrite=False,
            url="http://127.0.0.1:8188",
            json_output=False,
        )
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["name"] == "tiny (1).png"
        assert parsed["type"] == "input"

    def test_subfolder_traversal_rejected(self):
        """Client-side validation: `..` in subfolder must exit 3."""
        from comfyui_cli.commands.input_upload import run_upload
        from comfyui_cli.backend import ComfyValidationError

        with pytest.raises(ComfyValidationError) as ei:
            run_upload(
                file=FIXTURES / "tiny.png",
                subfolder="../escape",
                overwrite=False,
                url="http://127.0.0.1:8188",
                json_output=False,
            )
        assert ei.value.exit_code == 3

    def test_input_upload_url_flag_overrides_env(
        self, monkeypatch, httpx_mock: HTTPXMock
    ):
        """R3/R4: URL flag must override COMFY_URL env for input upload."""
        monkeypatch.setenv("COMFY_URL", "http://env-host:9999")
        httpx_mock.add_response(
            url="http://flag-host:8888/upload/image",
            method="POST",
            json={"name": "tiny.png", "subfolder": "", "type": "input"},
        )
        from comfyui_cli.commands.input_upload import run_upload

        run_upload(
            file=FIXTURES / "tiny.png",
            subfolder=None,
            overwrite=False,
            url="http://flag-host:8888",
            json_output=False,
        )
        req = httpx_mock.get_request()
        assert req is not None
        assert "flag-host" in str(req.url)
        assert "env-host" not in str(req.url)

    def test_overwrite_true_sends_string_true(self, httpx_mock: HTTPXMock):
        """Multipart form fields must be strings, not Python bool reprs."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/upload/image",
            method="POST",
            json={"name": "tiny.png", "subfolder": "", "type": "input"},
        )
        from comfyui_cli.commands.input_upload import run_upload

        run_upload(
            file=FIXTURES / "tiny.png",
            subfolder=None,
            overwrite=True,
            url="http://127.0.0.1:8188",
            json_output=False,
        )
        req = httpx_mock.get_request()
        assert req is not None
        body = req.read()
        # The value chunk after the overwrite field header
        assert b'name="overwrite"' in body
        after = body.split(b'name="overwrite"', 1)[1]
        # The field value `true` appears before the next boundary
        assert b"true" in after
        # Should NOT be the Python bool repr "True"
        # (be strict: the first 200 bytes after the header hold the value + boundary)
        assert b"True" not in after[:200]


# --- Tests: input list ------------------------------------------------------


class TestInputList:
    def test_missing_local_flag_errors_out(self):
        from comfyui_cli.commands.input_list import run_list
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_list(subfolder=None, local=False, url=None, json_output=False)
        assert ei.value.exit_code == 3
        msg = str(ei.value).lower()
        assert "local" in msg

    def test_with_local_lists_input_dir(self, monkeypatch, tmp_path, capsys):
        comfy_root = tmp_path / "ComfyUI"
        input_dir = comfy_root / "input"
        input_dir.mkdir(parents=True)
        (input_dir / "a.png").write_bytes(b"A")
        (input_dir / "b.png").write_bytes(b"BB")
        (input_dir / "sub").mkdir()
        (input_dir / "sub" / "c.png").write_bytes(b"CCC")

        monkeypatch.setenv("COMFY_ROOT", str(comfy_root))

        from comfyui_cli.commands.input_list import run_list

        run_list(subfolder=None, local=True, url=None, json_output=True)
        out = capsys.readouterr().out
        parsed = json.loads(out)
        names = {item["name"] for item in parsed}
        assert "a.png" in names
        assert "b.png" in names

    def test_input_list_missing_root_errors(self, monkeypatch, tmp_path):
        """R3/R4: COMFY_ROOT that doesn't exist must raise ComfyNotFoundError (exit 5)."""
        monkeypatch.setenv("COMFY_ROOT", str(tmp_path / "does_not_exist"))
        from comfyui_cli.commands.input_list import run_list
        from comfyui_cli.backend import ComfyNotFoundError

        with pytest.raises(ComfyNotFoundError) as ei:
            run_list(subfolder=None, local=True, url=None, json_output=False)
        assert ei.value.exit_code == 5

    def test_input_list_subfolder_traversal_rejected(
        self, monkeypatch, tmp_path
    ):
        """R3/R4: `..` in --subfolder must be rejected client-side (parallel to upload)."""
        comfy_root = tmp_path / "ComfyUI"
        (comfy_root / "input").mkdir(parents=True)
        monkeypatch.setenv("COMFY_ROOT", str(comfy_root))

        from comfyui_cli.commands.input_list import run_list
        from comfyui_cli.backend import ComfyValidationError

        with pytest.raises(ComfyValidationError) as ei:
            run_list(
                subfolder="../etc",
                local=True,
                url=None,
                json_output=False,
            )
        assert ei.value.exit_code == 3


# --- Tests: output download -------------------------------------------------


class TestOutputDownload:
    def _history_with_two_nodes(self, prompt_id: str) -> dict:
        return {
            prompt_id: {
                "prompt": [0, prompt_id, {}, {}, []],
                "outputs": {
                    "9": {
                        "images": [
                            {"filename": "a1.png", "subfolder": "", "type": "output"},
                            {"filename": "a2.png", "subfolder": "", "type": "output"},
                            {"filename": "a3.png", "subfolder": "", "type": "output"},
                        ]
                    },
                    "10": {
                        "images": [
                            {"filename": "b1.png", "subfolder": "", "type": "output"},
                            {"filename": "b2.png", "subfolder": "", "type": "output"},
                            {"filename": "b3.png", "subfolder": "", "type": "output"},
                        ]
                    },
                },
                "status": {"status_str": "success", "completed": True},
            }
        }

    def test_downloads_all_images(self, httpx_mock: HTTPXMock, tmp_path):
        prompt_id = "abc-123"
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json=self._history_with_two_nodes(prompt_id),
        )
        for name in ("a1.png", "a2.png", "a3.png", "b1.png", "b2.png", "b3.png"):
            httpx_mock.add_response(
                url=f"http://127.0.0.1:8188/view?filename={name}&subfolder=&type=output",
                content=f"BYTES-{name}".encode(),
            )
        from comfyui_cli.commands.output_download import run_download

        run_download(
            prompt_id=prompt_id,
            dest_dir=tmp_path,
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        target = tmp_path / prompt_id
        assert target.exists()
        saved = sorted(p.name for p in target.rglob("*.png"))
        assert len(saved) == 6
        assert "a1.png" in saved and "b3.png" in saved

    def test_missing_prompt_id_exits_5(self, httpx_mock: HTTPXMock, tmp_path):
        prompt_id = "missing"
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json={},
        )
        from comfyui_cli.commands.output_download import run_download
        from comfyui_cli.backend import ComfyNotFoundError

        with pytest.raises(ComfyNotFoundError) as ei:
            run_download(
                prompt_id=prompt_id,
                dest_dir=tmp_path,
                url="http://127.0.0.1:8188",
                json_output=False,
            )
        assert ei.value.exit_code == 5

    def test_uses_server_subfolder_when_downloading(
        self, httpx_mock: HTTPXMock, tmp_path
    ):
        prompt_id = "sub-test"
        history = {
            prompt_id: {
                "prompt": [0, prompt_id, {}, {}, []],
                "outputs": {
                    "9": {
                        "images": [
                            {
                                "filename": "z.png",
                                "subfolder": "nested/dir",
                                "type": "output",
                            }
                        ]
                    }
                },
                "status": {"status_str": "success", "completed": True},
            }
        }
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json=history,
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/view?filename=z.png&subfolder=nested/dir&type=output",
            content=b"ZZ",
        )
        from comfyui_cli.commands.output_download import run_download

        run_download(
            prompt_id=prompt_id,
            dest_dir=tmp_path,
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        view_reqs = [
            r for r in httpx_mock.get_requests() if r.url.path == "/view"
        ]
        assert len(view_reqs) == 1
        assert view_reqs[0].url.params.get("subfolder") == "nested/dir"

    def test_download_continues_on_single_404(
        self, httpx_mock: HTTPXMock, tmp_path
    ):
        """R3/R4: a 404 from /view on one ref must NOT abort the whole download.

        Successful siblings MUST still be written; the missing file MUST be
        skipped (not crash, not partial-write).
        """
        prompt_id = "abc-123"
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json={
                prompt_id: {
                    "prompt": [0, prompt_id, {}, {}, []],
                    "outputs": {
                        "9": {
                            "images": [
                                {
                                    "filename": "ok1.png",
                                    "subfolder": "",
                                    "type": "output",
                                },
                                {
                                    "filename": "missing.png",
                                    "subfolder": "",
                                    "type": "output",
                                },
                                {
                                    "filename": "ok3.png",
                                    "subfolder": "",
                                    "type": "output",
                                },
                            ]
                        }
                    },
                    "status": {
                        "status_str": "success",
                        "completed": True,
                        "messages": [],
                    },
                }
            },
        )
        # Existing test pattern: encode params in the URL string.
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/view?filename=ok1.png&subfolder=&type=output",
            content=b"img1",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/view?filename=missing.png&subfolder=&type=output",
            status_code=404,
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/view?filename=ok3.png&subfolder=&type=output",
            content=b"img3",
        )

        from comfyui_cli.commands.output_download import run_download

        run_download(
            prompt_id=prompt_id,
            dest_dir=tmp_path,
            url="http://127.0.0.1:8188",
            json_output=False,
        )

        saved_dir = tmp_path / prompt_id
        # The two successful files MUST be written; the missing one skipped.
        assert (saved_dir / "ok1.png").read_bytes() == b"img1"
        assert (saved_dir / "ok3.png").read_bytes() == b"img3"
        assert not (saved_dir / "missing.png").exists()

    def test_download_sends_origin_on_history_and_all_views(
        self, httpx_mock: HTTPXMock, tmp_path
    ):
        """R3/R4: Origin header must be set on BOTH /history and every /view."""
        prompt_id = "origin-test"
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json=self._history_with_two_nodes(prompt_id),
        )
        for name in ("a1.png", "a2.png", "a3.png", "b1.png", "b2.png", "b3.png"):
            httpx_mock.add_response(
                url=f"http://127.0.0.1:8188/view?filename={name}&subfolder=&type=output",
                content=b"ok",
            )
        from comfyui_cli.commands.output_download import run_download

        run_download(
            prompt_id=prompt_id,
            dest_dir=tmp_path,
            url="http://127.0.0.1:8188",
            json_output=False,
        )

        reqs = httpx_mock.get_requests()
        history_reqs = [r for r in reqs if r.url.path.startswith("/history")]
        view_reqs = [r for r in reqs if r.url.path == "/view"]
        assert len(history_reqs) == 1
        assert len(view_reqs) == 6
        assert (
            history_reqs[0].headers.get("Origin") == "http://127.0.0.1:8188"
        )
        for r in view_reqs:
            assert r.headers.get("Origin") == "http://127.0.0.1:8188"


# --- Tests: output show -----------------------------------------------------


class TestOutputShow:
    def test_outputs_section_only_printed_not_full_entry(
        self, httpx_mock: HTTPXMock, capsys
    ):
        prompt_id = "show-1"
        outputs = {
            "9": {
                "images": [
                    {"filename": "f.png", "subfolder": "", "type": "output"}
                ]
            }
        }
        history = {
            prompt_id: {
                "prompt": [0, prompt_id, {"secret": "should-not-leak"}, {}, []],
                "outputs": outputs,
                "meta": {"9": {"node_id": "9"}},
                "status": {"status_str": "success", "completed": True},
            }
        }
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json=history,
        )
        from comfyui_cli.commands.output_show import run_show

        run_show(
            prompt_id=prompt_id, url="http://127.0.0.1:8188", json_output=True
        )
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed == outputs
        assert "status_str" not in out
        assert "should-not-leak" not in out

    def test_missing_prompt_id_exits_5(self, httpx_mock: HTTPXMock):
        prompt_id = "nope"
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json={},
        )
        from comfyui_cli.commands.output_show import run_show
        from comfyui_cli.backend import ComfyNotFoundError

        with pytest.raises(ComfyNotFoundError) as ei:
            run_show(
                prompt_id=prompt_id,
                url="http://127.0.0.1:8188",
                json_output=False,
            )
        assert ei.value.exit_code == 5

    def test_output_show_sends_origin_on_history(
        self, httpx_mock: HTTPXMock
    ):
        """R3/R4: output show must set Origin on its /history call."""
        prompt_id = "origin-show"
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json={
                prompt_id: {
                    "prompt": [0, prompt_id, {}, {}, []],
                    "outputs": {
                        "9": {
                            "images": [
                                {
                                    "filename": "f.png",
                                    "subfolder": "",
                                    "type": "output",
                                }
                            ]
                        }
                    },
                    "status": {"status_str": "success", "completed": True},
                }
            },
        )
        from comfyui_cli.commands.output_show import run_show

        run_show(
            prompt_id=prompt_id,
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        req = httpx_mock.get_request()
        assert req is not None
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"


# --- Queue fixtures ---------------------------------------------------------


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _api_workflow() -> dict:
    """A minimal valid API-format workflow dict."""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {"seed": 5, "steps": 20},
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"},
        },
    }


def _queue_with_items() -> dict:
    """A /queue snapshot with 1 running + 2 pending."""
    return {
        "queue_running": [
            [
                0.0,
                "prompt-uuid-running",
                {"3": {"class_type": "KSampler", "inputs": {}}},
                {"client_id": "c1", "create_time": 1700000000000},
                ["9"],
            ]
        ],
        "queue_pending": [
            [
                1.0,
                "prompt-uuid-pending-1",
                {
                    "3": {"class_type": "KSampler", "inputs": {}},
                    "4": {"class_type": "VAEDecode", "inputs": {}},
                },
                {"client_id": "c2"},
                ["9"],
            ],
            [
                2.0,
                "prompt-uuid-pending-2",
                {"3": {"class_type": "KSampler", "inputs": {}}},
                {"client_id": "c3"},
                ["9"],
            ],
        ],
    }


def _queue_empty() -> dict:
    return {"queue_running": [], "queue_pending": []}


def _history_success(pid: str = "abcd1234") -> dict:
    return {
        pid: {
            "prompt": [
                0.0,
                pid,
                {"9": {"class_type": "SaveImage", "inputs": {}}},
                {"client_id": "c1"},
                ["9"],
                {},
            ],
            "outputs": {
                "9": {
                    "images": [
                        {
                            "filename": "ComfyUI_00001_.png",
                            "subfolder": "",
                            "type": "output",
                        }
                    ]
                }
            },
            "status": {
                "status_str": "success",
                "completed": True,
                "messages": [
                    [
                        "execution_start",
                        {"prompt_id": pid, "timestamp": 1700000000000},
                    ],
                    [
                        "execution_success",
                        {"prompt_id": pid, "timestamp": 1700000000100},
                    ],
                ],
            },
        }
    }


def _history_error(pid: str = "abcd1234") -> dict:
    return {
        pid: {
            "prompt": [
                0.0,
                pid,
                {"3": {"class_type": "KSampler", "inputs": {}}},
                {"client_id": "c1"},
                ["9"],
                {},
            ],
            "outputs": {},
            "status": {
                "status_str": "error",
                "completed": False,
                "messages": [
                    [
                        "execution_error",
                        {
                            "prompt_id": pid,
                            "node_id": "3",
                            "node_type": "KSampler",
                            "exception_message": "CUDA out of memory",
                            "exception_type": "torch.cuda.OutOfMemoryError",
                        },
                    ]
                ],
            },
        }
    }


# --- Tests: queue submit ----------------------------------------------------


class TestQueueSubmit:
    def test_submit_posts_to_prompt(self, httpx_mock: HTTPXMock, tmp_path):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            json={"prompt_id": "abcd1234", "number": 1, "node_errors": {}},
        )
        from comfyui_cli.commands.queue_submit import run_submit

        run_submit(file=workflow_path, url="http://127.0.0.1:8188")

        req = httpx_mock.get_request()
        assert req is not None
        assert req.method == "POST"
        assert str(req.url) == "http://127.0.0.1:8188/prompt"
        body = json.loads(req.content)
        assert "prompt" in body
        assert body["prompt"] == _api_workflow()
        assert "client_id" in body

    def test_submit_sends_origin_header(
        self, httpx_mock: HTTPXMock, tmp_path
    ):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            json={"prompt_id": "abcd1234", "number": 1, "node_errors": {}},
        )
        from comfyui_cli.commands.queue_submit import run_submit

        run_submit(file=workflow_path, url="http://127.0.0.1:8188")
        req = httpx_mock.get_request()
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"

    def test_submit_prints_prompt_id(
        self, httpx_mock: HTTPXMock, tmp_path, capsys
    ):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            json={"prompt_id": "abcd1234", "number": 1, "node_errors": {}},
        )
        from comfyui_cli.commands.queue_submit import run_submit

        run_submit(file=workflow_path, url="http://127.0.0.1:8188")
        out = capsys.readouterr().out
        assert "abcd1234" in out

    def test_submit_uses_provided_client_id(
        self, httpx_mock: HTTPXMock, tmp_path
    ):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            json={"prompt_id": "abcd1234", "number": 1, "node_errors": {}},
        )
        from comfyui_cli.commands.queue_submit import run_submit

        run_submit(
            file=workflow_path,
            url="http://127.0.0.1:8188",
            client_id="my-stable-id",
        )
        req = httpx_mock.get_request()
        body = json.loads(req.content)
        assert body["client_id"] == "my-stable-id"

    def test_submit_front_flag(self, httpx_mock: HTTPXMock, tmp_path):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            json={"prompt_id": "abcd1234", "number": 1, "node_errors": {}},
        )
        from comfyui_cli.commands.queue_submit import run_submit

        run_submit(
            file=workflow_path, url="http://127.0.0.1:8188", front=True
        )
        req = httpx_mock.get_request()
        body = json.loads(req.content)
        assert body["front"] is True

    def test_submit_detects_ui_format(self, tmp_path):
        """UI format (nodes+links) must fail with exit 3 before any HTTP call."""
        ui_path = tmp_path / "ui.json"
        ui_path.write_text(json.dumps({"nodes": [{"id": 1}], "links": []}))
        from comfyui_cli.commands.queue_submit import run_submit
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_submit(file=ui_path, url="http://127.0.0.1:8188")
        assert ei.value.exit_code == 3
        msg = str(ei.value).lower()
        assert (
            "ui-format" in msg or "ui format" in msg or "api format" in msg
        )

    def test_submit_file_not_found(self, tmp_path):
        from comfyui_cli.commands.queue_submit import run_submit
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError):
            run_submit(
                file=tmp_path / "does_not_exist.json",
                url="http://127.0.0.1:8188",
            )

    def test_submit_invalid_json_file(self, tmp_path):
        bad = tmp_path / "bad.txt"
        bad.write_text("not json at all")
        from comfyui_cli.commands.queue_submit import run_submit
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError):
            run_submit(file=bad, url="http://127.0.0.1:8188")

    def test_submit_surfaces_node_errors_400(
        self, httpx_mock: HTTPXMock, tmp_path
    ):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            status_code=400,
            json={
                "error": {
                    "type": "prompt_outputs_failed_validation",
                    "message": "Prompt outputs failed validation",
                    "details": "",
                    "extra_info": {},
                },
                "node_errors": {
                    "4": {
                        "errors": [
                            {"type": "value_not_in_list", "message": "not found"}
                        ],
                        "dependent_outputs": ["9"],
                        "class_type": "CheckpointLoaderSimple",
                    }
                },
            },
        )
        from comfyui_cli.commands.queue_submit import run_submit
        from comfyui_cli.backend import ComfyValidationError

        with pytest.raises(ComfyValidationError) as ei:
            run_submit(file=workflow_path, url="http://127.0.0.1:8188")
        assert ei.value.exit_code == 3
        assert "4" in ei.value.node_errors

    def test_submit_json_output(
        self, httpx_mock: HTTPXMock, tmp_path, capsys
    ):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            json={"prompt_id": "abcd1234", "number": 1, "node_errors": {}},
        )
        from comfyui_cli.commands.queue_submit import run_submit

        run_submit(
            file=workflow_path,
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["prompt_id"] == "abcd1234"
        assert "client_id" in parsed


# --- Tests: queue status / list ---------------------------------------------


class TestQueueStatus:
    def test_status_no_id_fetches_queue(
        self, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            json=_queue_with_items(),
        )
        from comfyui_cli.commands.queue_status import run_status

        run_status(
            prompt_id=None,
            url="http://127.0.0.1:8188",
            json_output=False,
        )
        out = capsys.readouterr().out
        assert "prompt-uuid-running" in out
        assert "prompt-uuid-pending-1" in out
        assert "prompt-uuid-pending-2" in out

    def test_status_no_id_uses_get(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            json=_queue_empty(),
        )
        from comfyui_cli.commands.queue_status import run_status

        run_status(
            prompt_id=None,
            url="http://127.0.0.1:8188",
            json_output=False,
        )
        req = httpx_mock.get_request()
        assert req.method == "GET"

    def test_status_no_id_origin_header(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            json=_queue_empty(),
        )
        from comfyui_cli.commands.queue_status import run_status

        run_status(
            prompt_id=None,
            url="http://127.0.0.1:8188",
            json_output=False,
        )
        req = httpx_mock.get_request()
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"

    def test_status_empty_queue_ok(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            json=_queue_empty(),
        )
        from comfyui_cli.commands.queue_status import run_status

        run_status(
            prompt_id=None,
            url="http://127.0.0.1:8188",
            json_output=False,
        )

    def test_status_with_id_success(
        self, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234",
            json=_history_success("abcd1234"),
        )
        from comfyui_cli.commands.queue_status import run_status

        run_status(
            prompt_id="abcd1234",
            url="http://127.0.0.1:8188",
            json_output=False,
        )
        out = capsys.readouterr().out
        assert "success" in out.lower()

    def test_status_with_id_error_exits_4(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234",
            json=_history_error("abcd1234"),
        )
        from comfyui_cli.commands.queue_status import run_status
        from comfyui_cli.backend import ComfyExecutionError

        with pytest.raises(ComfyExecutionError) as ei:
            run_status(
                prompt_id="abcd1234",
                url="http://127.0.0.1:8188",
                json_output=False,
            )
        assert ei.value.exit_code == 4

    def test_status_with_id_missing_exits_5(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/unknown",
            json={},
        )
        from comfyui_cli.commands.queue_status import run_status
        from comfyui_cli.backend import ComfyNotFoundError

        with pytest.raises(ComfyNotFoundError) as ei:
            run_status(
                prompt_id="unknown",
                url="http://127.0.0.1:8188",
                json_output=False,
            )
        assert ei.value.exit_code == 5

    def test_status_json_output_passthrough(
        self, httpx_mock: HTTPXMock, capsys
    ):
        payload = _queue_with_items()
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            json=payload,
        )
        from comfyui_cli.commands.queue_status import run_status

        run_status(
            prompt_id=None,
            url="http://127.0.0.1:8188",
            json_output=True,
        )
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed == payload


class TestQueueList:
    def test_list_fetches_queue(self, httpx_mock: HTTPXMock, capsys):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            json=_queue_with_items(),
        )
        from comfyui_cli.commands.queue_list import run_list

        run_list(url="http://127.0.0.1:8188", json_output=False)
        out = capsys.readouterr().out
        assert "prompt-uuid-running" in out

    def test_list_sends_origin_header(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            json=_queue_empty(),
        )
        from comfyui_cli.commands.queue_list import run_list

        run_list(url="http://127.0.0.1:8188", json_output=False)
        req = httpx_mock.get_request()
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"


# --- Tests: queue wait ------------------------------------------------------


class TestQueueWait:
    def test_wait_polls_until_history_appears(
        self, httpx_mock: HTTPXMock, monkeypatch
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234", json={}
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234", json={}
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234", json={}
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234",
            json=_history_success("abcd1234"),
        )
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        from comfyui_cli.commands.queue_wait import run_wait

        run_wait(
            prompt_id="abcd1234",
            url="http://127.0.0.1:8188",
            timeout=5.0,
            live=False,
        )
        reqs = httpx_mock.get_requests()
        assert len(reqs) == 4

    def test_wait_exit_4_on_execution_error(
        self, httpx_mock: HTTPXMock, monkeypatch
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234",
            json=_history_error("abcd1234"),
        )
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        from comfyui_cli.commands.queue_wait import run_wait
        from comfyui_cli.backend import ComfyExecutionError

        with pytest.raises(ComfyExecutionError) as ei:
            run_wait(
                prompt_id="abcd1234",
                url="http://127.0.0.1:8188",
                timeout=5.0,
                live=False,
            )
        assert ei.value.exit_code == 4

    def test_wait_timeout_exits_1(
        self, httpx_mock: HTTPXMock, monkeypatch
    ):
        # is_reusable=True lets the same mock match multiple polls.
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234",
            json={},
            is_reusable=True,
        )
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        from comfyui_cli.commands.queue_wait import run_wait
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_wait(
                prompt_id="abcd1234",
                url="http://127.0.0.1:8188",
                timeout=0.05,
                live=False,
            )
        assert ei.value.exit_code == 1
        assert "timed out" in str(ei.value).lower()

    def test_wait_origin_header(
        self, httpx_mock: HTTPXMock, monkeypatch
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234",
            json=_history_success("abcd1234"),
        )
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        from comfyui_cli.commands.queue_wait import run_wait

        run_wait(
            prompt_id="abcd1234",
            url="http://127.0.0.1:8188",
            timeout=5.0,
            live=False,
        )
        req = httpx_mock.get_request()
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"

    def test_live_returns_immediately_when_history_already_success(
        self, httpx_mock: HTTPXMock, monkeypatch
    ):
        """Race guard: if /history shows success before ws connects, skip ws."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234",
            json=_history_success("abcd1234"),
        )

        connect_called = {"val": False}

        def _never_connect(self, *a, **kw):
            connect_called["val"] = True
            raise AssertionError("ws must not be connected when history is ready")

        monkeypatch.setattr(
            "comfyui_cli.ws_client.ComfyWsClient.connect", _never_connect
        )

        from comfyui_cli.commands.queue_wait import run_wait

        run_wait(
            prompt_id="abcd1234",
            url="http://127.0.0.1:8188",
            timeout=5.0,
            live=True,
        )
        assert connect_called["val"] is False

    def test_live_raises_execution_error_when_history_already_errored(
        self, httpx_mock: HTTPXMock, monkeypatch
    ):
        """Race guard: history shows error before ws -> raise without connecting."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/abcd1234",
            json=_history_error("abcd1234"),
        )

        def _never_connect(self, *a, **kw):
            raise AssertionError("ws must not be connected when history is ready")

        monkeypatch.setattr(
            "comfyui_cli.ws_client.ComfyWsClient.connect", _never_connect
        )

        from comfyui_cli.commands.queue_wait import run_wait
        from comfyui_cli.backend import ComfyExecutionError

        with pytest.raises(ComfyExecutionError) as ei:
            run_wait(
                prompt_id="abcd1234",
                url="http://127.0.0.1:8188",
                timeout=5.0,
                live=True,
            )
        assert ei.value.exit_code == 4


# --- Tests: ws_client -------------------------------------------------------


class _FakeWs:
    """Fake websocket object: recv() yields from a list of frames.

    Strings/bytes are returned verbatim; callables are called (used for raising
    exceptions). Once the list is exhausted, recv() raises IndexError so tests
    fail loudly rather than hanging.
    """

    def __init__(self, frames):
        self._frames = list(frames)
        self.closed = False

    def recv(self):
        if not self._frames:
            raise IndexError("FakeWs frames exhausted")
        nxt = self._frames.pop(0)
        if callable(nxt):
            return nxt()
        return nxt

    def connect(self, *a, **kw):
        pass

    def settimeout(self, *a, **kw):
        pass

    def close(self):
        self.closed = True


def _install_fake_ws(monkeypatch, fake_ws):
    """Monkeypatch websocket.WebSocket so connect() returns our fake."""
    import websocket

    def _factory():
        return fake_ws

    monkeypatch.setattr(websocket, "WebSocket", _factory)


class TestWsClient:
    def test_watch_returns_success_on_execution_success_event(
        self, monkeypatch
    ):
        frames = [
            json.dumps(
                {
                    "type": "execution_success",
                    "data": {"prompt_id": "abc"},
                }
            )
        ]
        _install_fake_ws(monkeypatch, _FakeWs(frames))

        from comfyui_cli.ws_client import ComfyWsClient

        ws = ComfyWsClient("http://127.0.0.1:8188", client_id="cid")
        ws.connect(timeout=1.0)
        result = ws.watch(prompt_id="abc", timeout=1.0)
        assert result["status_str"] == "success"

    def test_watch_returns_success_on_executing_null_terminator(
        self, monkeypatch
    ):
        frames = [
            json.dumps(
                {
                    "type": "executing",
                    "data": {"node": None, "prompt_id": "abc"},
                }
            )
        ]
        _install_fake_ws(monkeypatch, _FakeWs(frames))

        from comfyui_cli.ws_client import ComfyWsClient

        ws = ComfyWsClient("http://127.0.0.1:8188", client_id="cid")
        ws.connect(timeout=1.0)
        result = ws.watch(prompt_id="abc", timeout=1.0)
        assert result["status_str"] == "success"

    def test_watch_returns_error_on_execution_error(self, monkeypatch):
        frames = [
            json.dumps(
                {
                    "type": "execution_error",
                    "data": {
                        "prompt_id": "abc",
                        "exception_type": "RuntimeError",
                        "exception_message": "CUDA OOM",
                    },
                }
            )
        ]
        _install_fake_ws(monkeypatch, _FakeWs(frames))

        from comfyui_cli.ws_client import ComfyWsClient

        ws = ComfyWsClient("http://127.0.0.1:8188", client_id="cid")
        ws.connect(timeout=1.0)
        result = ws.watch(prompt_id="abc", timeout=1.0)
        assert result["status_str"] == "error"
        assert "CUDA OOM" in (result.get("detail") or "")

    def test_watch_returns_interrupted(self, monkeypatch):
        frames = [
            json.dumps(
                {
                    "type": "execution_interrupted",
                    "data": {"prompt_id": "abc"},
                }
            )
        ]
        _install_fake_ws(monkeypatch, _FakeWs(frames))

        from comfyui_cli.ws_client import ComfyWsClient

        ws = ComfyWsClient("http://127.0.0.1:8188", client_id="cid")
        ws.connect(timeout=1.0)
        result = ws.watch(prompt_id="abc", timeout=1.0)
        assert result["status_str"] == "interrupted"

    def test_watch_ignores_events_for_other_prompt_ids(self, monkeypatch):
        frames = [
            json.dumps(
                {
                    "type": "execution_success",
                    "data": {"prompt_id": "OTHER"},
                }
            ),
            json.dumps(
                {
                    "type": "execution_success",
                    "data": {"prompt_id": "abc"},
                }
            ),
        ]
        _install_fake_ws(monkeypatch, _FakeWs(frames))

        from comfyui_cli.ws_client import ComfyWsClient

        ws = ComfyWsClient("http://127.0.0.1:8188", client_id="cid")
        ws.connect(timeout=1.0)
        result = ws.watch(prompt_id="abc", timeout=1.0)
        assert result["status_str"] == "success"

    def test_watch_binary_frames_are_ignored(self, monkeypatch):
        frames = [
            b"\x89PNG-preview-binary",
            json.dumps(
                {
                    "type": "execution_success",
                    "data": {"prompt_id": "abc"},
                }
            ),
        ]
        _install_fake_ws(monkeypatch, _FakeWs(frames))

        from comfyui_cli.ws_client import ComfyWsClient

        ws = ComfyWsClient("http://127.0.0.1:8188", client_id="cid")
        ws.connect(timeout=1.0)
        result = ws.watch(prompt_id="abc", timeout=1.0)
        assert result["status_str"] == "success"

    def test_watch_ws_timeout_raises_connection_error(self, monkeypatch):
        """ws recv timeout must surface as ComfyConnectionError, not RuntimeError."""
        import websocket

        def _raise_timeout():
            raise websocket.WebSocketTimeoutException("timed out")

        _install_fake_ws(monkeypatch, _FakeWs([_raise_timeout]))

        from comfyui_cli.ws_client import ComfyWsClient
        from comfyui_cli.backend import ComfyConnectionError

        ws = ComfyWsClient("http://127.0.0.1:8188", client_id="cid")
        ws.connect(timeout=1.0)
        with pytest.raises(ComfyConnectionError) as ei:
            ws.watch(prompt_id="abc", timeout=1.0)
        assert ei.value.exit_code == 2


# --- Tests: queue cancel ----------------------------------------------------


class TestQueueCancel:
    def test_cancel_deletes_then_interrupts(
        self, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="POST",
            status_code=200,
            text="",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/interrupt",
            method="POST",
            status_code=200,
            text="",
        )
        from comfyui_cli.commands.queue_cancel import run_cancel

        run_cancel(prompt_id="abcd1234", url="http://127.0.0.1:8188")

        reqs = httpx_mock.get_requests()
        assert len(reqs) == 2
        assert reqs[0].method == "POST"
        assert str(reqs[0].url) == "http://127.0.0.1:8188/queue"
        delete_body = json.loads(reqs[0].content)
        assert delete_body == {"delete": ["abcd1234"]}
        assert reqs[1].method == "POST"
        assert str(reqs[1].url) == "http://127.0.0.1:8188/interrupt"
        interrupt_body = json.loads(reqs[1].content)
        assert interrupt_body == {"prompt_id": "abcd1234"}

    def test_cancel_prints_id(self, httpx_mock: HTTPXMock, capsys):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="POST",
            text="",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/interrupt",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_cancel import run_cancel

        run_cancel(prompt_id="abcd1234", url="http://127.0.0.1:8188")
        out = capsys.readouterr().out
        assert "abcd1234" in out

    def test_cancel_sends_origin_header(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="POST",
            text="",
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/interrupt",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_cancel import run_cancel

        run_cancel(prompt_id="abcd1234", url="http://127.0.0.1:8188")
        reqs = httpx_mock.get_requests()
        assert reqs[0].headers.get("Origin") == "http://127.0.0.1:8188"
        assert reqs[1].headers.get("Origin") == "http://127.0.0.1:8188"


# --- Tests: queue clear -----------------------------------------------------


class TestQueueClear:
    def test_clear_counts_before(
        self, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="GET",
            json=_queue_with_items(),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_clear import run_clear

        run_clear(url="http://127.0.0.1:8188")
        out = capsys.readouterr().out
        # 2 pending in _queue_with_items
        assert "2" in out
        assert "clear" in out.lower()

        reqs = httpx_mock.get_requests()
        assert len(reqs) == 2
        assert reqs[0].method == "GET"
        assert reqs[1].method == "POST"
        post_body = json.loads(reqs[1].content)
        assert post_body == {"clear": True}

    def test_clear_empty_queue(self, httpx_mock: HTTPXMock, capsys):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="GET",
            json=_queue_empty(),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_clear import run_clear

        run_clear(url="http://127.0.0.1:8188")
        out = capsys.readouterr().out
        assert "0" in out

    def test_clear_sends_origin_header(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="GET",
            json=_queue_empty(),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_clear import run_clear

        run_clear(url="http://127.0.0.1:8188")
        reqs = httpx_mock.get_requests()
        for r in reqs:
            assert r.headers.get("Origin") == "http://127.0.0.1:8188"


# --- Tests: queue free ------------------------------------------------------


class TestQueueFree:
    def test_free_with_unload_models(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/free",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_free import run_free

        run_free(
            url="http://127.0.0.1:8188",
            unload_models=True,
            free_memory=False,
        )
        req = httpx_mock.get_request()
        body = json.loads(req.content)
        assert body == {"unload_models": True, "free_memory": False}

    def test_free_with_free_memory(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/free",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_free import run_free

        run_free(
            url="http://127.0.0.1:8188",
            unload_models=False,
            free_memory=True,
        )
        req = httpx_mock.get_request()
        body = json.loads(req.content)
        assert body == {"unload_models": False, "free_memory": True}

    def test_free_neither_flag_exits_1(self, httpx_mock: HTTPXMock):
        """No flags = no-op warning to stderr, exit 1."""
        from comfyui_cli.commands.queue_free import run_free
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_free(
                url="http://127.0.0.1:8188",
                unload_models=False,
                free_memory=False,
            )
        assert ei.value.exit_code == 1
        msg = str(ei.value).lower()
        assert "no-op" in msg or "no flags" in msg

    def test_free_sends_origin_header(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/free",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_free import run_free

        run_free(
            url="http://127.0.0.1:8188",
            unload_models=True,
            free_memory=True,
        )
        req = httpx_mock.get_request()
        assert req.headers.get("Origin") == "http://127.0.0.1:8188"

    def test_free_uses_post(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/free",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_free import run_free

        run_free(
            url="http://127.0.0.1:8188",
            unload_models=True,
            free_memory=True,
        )
        req = httpx_mock.get_request()
        assert req.method == "POST"


# --- Tests: queue URL precedence (flag > env > default) ---------------------


class TestQueueUrlPrecedence:
    def test_submit_url_flag_overrides_env(
        self, monkeypatch, httpx_mock: HTTPXMock, tmp_path
    ):
        monkeypatch.setenv("COMFY_URL", "http://env-host:9999")
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://flag-host:8888/prompt",
            json={"prompt_id": "abcd1234", "number": 1, "node_errors": {}},
        )
        from comfyui_cli.commands.queue_submit import run_submit

        run_submit(file=workflow_path, url="http://flag-host:8888")
        req = httpx_mock.get_request()
        assert req is not None
        assert "flag-host" in str(req.url)

    def test_status_env_used_when_no_flag(
        self, monkeypatch, httpx_mock: HTTPXMock
    ):
        monkeypatch.setenv("COMFY_URL", "http://env-host:7777")
        httpx_mock.add_response(
            url="http://env-host:7777/queue",
            json=_queue_empty(),
        )
        from comfyui_cli.commands.queue_status import run_status

        run_status(prompt_id=None, url=None, json_output=False)
        req = httpx_mock.get_request()
        assert req is not None
        assert "env-host" in str(req.url)

    def test_clear_uses_default_url_when_nothing_set(
        self, monkeypatch, httpx_mock: HTTPXMock
    ):
        monkeypatch.delenv("COMFY_URL", raising=False)
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="GET",
            json=_queue_empty(),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/queue",
            method="POST",
            text="",
        )
        from comfyui_cli.commands.queue_clear import run_clear

        run_clear(url=None)
        reqs = httpx_mock.get_requests()
        assert len(reqs) >= 1
        for r in reqs:
            assert "127.0.0.1:8188" in str(r.url)


# --- Tests: queue submit — front flag default & client_id shape --------------


class TestQueueSubmitDetails:
    def test_submit_omits_front_when_default(
        self, httpx_mock: HTTPXMock, tmp_path
    ):
        """Without --front the request body must not include a truthy `front`.

        The server treats absence and `false` equivalently; this test accepts
        either: the key is absent, or it is present and falsy.
        """
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            json={"prompt_id": "abcd1234", "number": 1, "node_errors": {}},
        )
        from comfyui_cli.commands.queue_submit import run_submit

        run_submit(file=workflow_path, url="http://127.0.0.1:8188")
        req = httpx_mock.get_request()
        body = json.loads(req.content)
        assert not body.get("front")

    def test_submit_auto_client_id_is_valid_uuid(
        self, httpx_mock: HTTPXMock, tmp_path
    ):
        """Auto-generated client_id must be a parseable UUID."""
        import uuid as _uuid

        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            json={"prompt_id": "abcd1234", "number": 1, "node_errors": {}},
        )
        from comfyui_cli.commands.queue_submit import run_submit

        run_submit(file=workflow_path, url="http://127.0.0.1:8188")
        req = httpx_mock.get_request()
        body = json.loads(req.content)
        # Raises ValueError on invalid UUID.
        _uuid.UUID(body["client_id"])


# --- Tests: workflow run (compose: submit + wait + download) ----------------


class TestWorkflowRun:
    """End-to-end compose path: /prompt -> /history polling -> /view."""

    PROMPT_ID = "wfrun-abc-1"

    def _mock_happy_path(
        self,
        httpx_mock: HTTPXMock,
        *,
        prompt_id: str = "wfrun-abc-1",
        image_bytes: bytes = b"PNG-bytes",
    ) -> None:
        """Wire up /prompt, a 2-phase /history poll, and one /view image."""
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            method="POST",
            json={"prompt_id": prompt_id, "number": 1, "node_errors": {}},
        )
        # First /history poll returns empty; second returns success.
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}", json={}
        )
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json=_history_success(prompt_id),
        )
        # output_download re-fetches /history, then grabs /view.
        httpx_mock.add_response(
            url=f"http://127.0.0.1:8188/history/{prompt_id}",
            json=_history_success(prompt_id),
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/view?filename=ComfyUI_00001_.png&subfolder=&type=output",
            content=image_bytes,
        )

    def test_json_file_compose_end_to_end(
        self, httpx_mock: HTTPXMock, monkeypatch, tmp_path, capsys
    ):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        self._mock_happy_path(httpx_mock)

        from comfyui_cli.commands.workflow_run import run_run

        run_run(
            file=workflow_path,
            url="http://127.0.0.1:8188",
            live=False,
            output_dir=tmp_path / "out",
            timeout=5.0,
            json_output=True,
        )
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["prompt_id"] == self.PROMPT_ID
        assert parsed["status"] == "success"
        assert len(parsed["outputs"]) == 1
        saved_path = Path(parsed["outputs"][0]["path"])
        assert saved_path.is_file()
        assert saved_path.read_bytes() == b"PNG-bytes"

    def test_submit_sends_api_workflow_body(
        self, httpx_mock: HTTPXMock, monkeypatch, tmp_path
    ):
        """The POST /prompt body must equal the loaded workflow dict."""
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        self._mock_happy_path(httpx_mock)

        from comfyui_cli.commands.workflow_run import run_run

        run_run(
            file=workflow_path,
            url="http://127.0.0.1:8188",
            live=False,
            output_dir=tmp_path / "out",
            timeout=5.0,
            json_output=True,
        )
        prompt_reqs = [
            r
            for r in httpx_mock.get_requests()
            if r.method == "POST" and r.url.path == "/prompt"
        ]
        assert len(prompt_reqs) == 1
        body = json.loads(prompt_reqs[0].content)
        assert body["prompt"] == _api_workflow()

    def test_png_extraction_path_submits_embedded_workflow(
        self,
        httpx_mock: HTTPXMock,
        monkeypatch,
        tmp_path,
        png_with_workflow,
    ):
        """A .png input triggers extract_api_dict then submit."""
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        self._mock_happy_path(httpx_mock)

        from comfyui_cli.commands.workflow_run import run_run

        run_run(
            file=png_with_workflow,
            url="http://127.0.0.1:8188",
            live=False,
            output_dir=tmp_path / "out",
            timeout=5.0,
            json_output=True,
        )
        prompt_reqs = [
            r
            for r in httpx_mock.get_requests()
            if r.method == "POST" and r.url.path == "/prompt"
        ]
        assert len(prompt_reqs) == 1
        body = json.loads(prompt_reqs[0].content)
        # Embedded API workflow is the conftest _API_WORKFLOW — node ids 3..7.
        assert "3" in body["prompt"]
        assert body["prompt"]["3"]["class_type"] == "KSampler"

    def test_ui_format_json_exits_3(self, tmp_path):
        ui_path = tmp_path / "ui.json"
        ui_path.write_text(json.dumps({"nodes": [{"id": 1}], "links": []}))
        from comfyui_cli.commands.workflow_run import run_run
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_run(
                file=ui_path,
                url="http://127.0.0.1:8188",
                live=False,
                timeout=5.0,
            )
        assert ei.value.exit_code == 3

    def test_png_without_workflow_exits_5(
        self, tmp_path, png_without_workflow
    ):
        from comfyui_cli.commands.workflow_run import run_run
        from comfyui_cli.backend import ComfyNotFoundError

        with pytest.raises(ComfyNotFoundError) as ei:
            run_run(
                file=png_without_workflow,
                url="http://127.0.0.1:8188",
                live=False,
                timeout=5.0,
            )
        assert ei.value.exit_code == 5

    def test_execution_error_exits_4(
        self, httpx_mock: HTTPXMock, monkeypatch, tmp_path
    ):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            method="POST",
            json={"prompt_id": "err-1", "number": 1, "node_errors": {}},
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/err-1",
            json=_history_error("err-1"),
        )
        from comfyui_cli.commands.workflow_run import run_run
        from comfyui_cli.backend import ComfyExecutionError

        with pytest.raises(ComfyExecutionError) as ei:
            run_run(
                file=workflow_path,
                url="http://127.0.0.1:8188",
                live=False,
                output_dir=tmp_path / "out",
                timeout=5.0,
            )
        assert ei.value.exit_code == 4

    def test_timeout_exits_1(
        self, httpx_mock: HTTPXMock, monkeypatch, tmp_path
    ):
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/prompt",
            method="POST",
            json={"prompt_id": "t-1", "number": 1, "node_errors": {}},
        )
        httpx_mock.add_response(
            url="http://127.0.0.1:8188/history/t-1",
            json={},
            is_reusable=True,
        )
        from comfyui_cli.commands.workflow_run import run_run
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError) as ei:
            run_run(
                file=workflow_path,
                url="http://127.0.0.1:8188",
                live=False,
                output_dir=tmp_path / "out",
                timeout=0.05,
            )
        assert ei.value.exit_code == 1
        assert "timed out" in str(ei.value).lower()

    def test_no_live_uses_history_polling(
        self, httpx_mock: HTTPXMock, monkeypatch, tmp_path
    ):
        """--no-live must never attempt a websocket connection."""
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        self._mock_happy_path(httpx_mock)

        # Make ComfyWsClient.connect blow up if anyone invokes it.
        def _boom(*a, **kw):
            raise AssertionError("websocket must not be used with --no-live")

        monkeypatch.setattr(
            "comfyui_cli.ws_client.ComfyWsClient.connect", _boom
        )

        from comfyui_cli.commands.workflow_run import run_run

        run_run(
            file=workflow_path,
            url="http://127.0.0.1:8188",
            live=False,
            output_dir=tmp_path / "out",
            timeout=5.0,
            json_output=True,
        )
        # Sanity: only /history + /view were hit (plus /prompt).
        paths = [r.url.path for r in httpx_mock.get_requests()]
        assert "/prompt" in paths
        assert any(p.startswith("/history/") for p in paths)
        assert "/view" in paths

    def test_client_id_preserved_across_submit_and_wait(
        self, httpx_mock: HTTPXMock, monkeypatch, tmp_path
    ):
        """A user-supplied --client-id must round-trip unchanged to /prompt."""
        workflow_path = tmp_path / "wf.json"
        workflow_path.write_text(json.dumps(_api_workflow()))
        monkeypatch.setattr(
            "comfyui_cli.commands.queue_wait.POLL_INTERVAL", 0.01
        )
        self._mock_happy_path(httpx_mock)

        from comfyui_cli.commands.workflow_run import run_run

        run_run(
            file=workflow_path,
            url="http://127.0.0.1:8188",
            live=False,
            output_dir=tmp_path / "out",
            client_id="stable-agent-id",
            timeout=5.0,
            json_output=True,
        )
        prompt_reqs = [
            r
            for r in httpx_mock.get_requests()
            if r.method == "POST" and r.url.path == "/prompt"
        ]
        body = json.loads(prompt_reqs[0].content)
        assert body["client_id"] == "stable-agent-id"
