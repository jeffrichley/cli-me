"""Shared fixtures for ComfyUI QA tests.

Makes `scripts/` importable for `from comfyui_cli...` and provides PNG/WebP
fixtures with embedded workflows for workflow-extract tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

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


# --- Canonical workflow dicts used inside PNG/WebP fixtures -----------------

_API_WORKFLOW = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 8,
            "denoise": 1,
            "seed": 8566257,
            "steps": 20,
            "sampler_name": "euler",
            "scheduler": "normal",
            "model": ["4", 0],
            "latent_image": ["5", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
        },
        "_meta": {"title": "KSampler"},
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {"batch_size": 1, "height": 512, "width": 512},
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["4", 1], "text": "a cat"},
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["4", 1], "text": "bad hands"},
    },
}

_UI_WORKFLOW = {
    "last_node_id": 7,
    "last_link_id": 1,
    "nodes": [{"id": 1, "type": "KSampler"}],
    "links": [],
    "groups": [],
    "config": {},
    "extra": {},
    "version": 0.4,
}


@pytest.fixture
def sample_api_workflow() -> dict:
    return json.loads(json.dumps(_API_WORKFLOW))


@pytest.fixture
def sample_ui_workflow() -> dict:
    return json.loads(json.dumps(_UI_WORKFLOW))


@pytest.fixture
def png_with_workflow(tmp_path) -> Path:
    """Create a tiny PNG with `prompt` and `workflow` tEXt chunks."""
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo

    meta = PngInfo()
    meta.add_text("prompt", json.dumps(_API_WORKFLOW))
    meta.add_text("workflow", json.dumps(_UI_WORKFLOW))

    out = tmp_path / "sample_with_workflow.png"
    img = Image.new("RGB", (4, 4), "black")
    img.save(out, pnginfo=meta)
    return out


@pytest.fixture
def png_without_workflow(tmp_path) -> Path:
    """PNG with no metadata chunks — represents `--disable-metadata` case."""
    from PIL import Image

    out = tmp_path / "no_workflow.png"
    Image.new("RGB", (4, 4), "black").save(out)
    return out


@pytest.fixture
def webp_with_workflow(tmp_path) -> Path:
    """Create a tiny WebP with prompt at 0x0110 and workflow at 0x010F (EXIF)."""
    from PIL import Image

    exif = Image.Exif()
    # Model tag — API prompt per _ui.py:129
    exif[0x0110] = "prompt:" + json.dumps(_API_WORKFLOW)
    # Make tag (descending from 0x010F) — UI workflow per _ui.py:131-134
    exif[0x010F] = "workflow:" + json.dumps(_UI_WORKFLOW)

    out = tmp_path / "sample_with_workflow.webp"
    img = Image.new("RGB", (4, 4), "black")
    img.save(out, format="WEBP", exif=exif.tobytes())
    return out


@pytest.fixture
def webp_with_workflow_at_offset(tmp_path) -> Path:
    """WebP where `workflow:` lands at tag 0x010D (descending), not 0x010F.

    ComfyUI writes `extra_pnginfo` entries at descending tags starting from
    0x010F in dict-iteration order. If `workflow` is the THIRD entry, it ends
    up at 0x010D. Exercises the descending-scan code path in _extract_webp.
    """
    from PIL import Image

    # Use a dict with workflow as the third key — mirrors the order ComfyUI
    # would produce if two other extra_pnginfo chunks precede workflow.
    extra_pnginfo = {
        "decoy_a": {"unused": 1},
        "decoy_b": {"unused": 2},
        "workflow": _UI_WORKFLOW,
    }

    exif = Image.Exif()
    # Model tag — API prompt (fixed at 0x0110)
    exif[0x0110] = "prompt:" + json.dumps(_API_WORKFLOW)
    # Descending assignment from 0x010F, in dict-iteration order.
    tag = 0x010F
    for key, payload in extra_pnginfo.items():
        exif[tag] = f"{key}:" + json.dumps(payload)
        tag -= 1
    # Sanity: workflow should now be at 0x010D.
    assert exif.get(0x010D, "").startswith("workflow:")

    out = tmp_path / "sample_with_workflow_offset.webp"
    img = Image.new("RGB", (4, 4), "black")
    img.save(out, format="WEBP", exif=exif.tobytes())
    return out


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR
