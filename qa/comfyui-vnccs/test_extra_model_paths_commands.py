"""Tier 1 tests for extra_model_paths.yaml parsing + check_models integration.

Covers backend.parse_extra_model_paths + backend.find_model_path so that
``vnccs check models`` finds files redirected via ComfyUI's
``extra_model_paths.yaml`` mechanism (``base_path`` + per-model-type
subdirs). Bug found in the field: the user has all VNCCS models living
at ``E:/data/comfy/models/`` but the wrapper was probing
``<COMFY_PATH>/models/`` only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vnccs_cli import backend
from vnccs_cli.commands import check_models


# ---------------------------------------------------------------------------
# parse_extra_model_paths
# ---------------------------------------------------------------------------


def test_parse_extra_model_paths_missing_yaml_returns_empty(tmp_path):
    """No YAML file → no extra search dirs."""
    result = backend.parse_extra_model_paths(tmp_path)
    assert result == []


def test_parse_extra_model_paths_simple_section(tmp_path):
    base = tmp_path / "altmodels"
    base.mkdir()
    (tmp_path / "extra_model_paths.yaml").write_text(
        f"""\
models:
    base_path: {base}
    is_default: true
    checkpoints: checkpoints/
    loras: loras/
""",
        encoding="utf-8",
    )
    result = backend.parse_extra_model_paths(tmp_path)
    type_to_dirs = {t: d for t, d in result}
    assert ("checkpoints", base / "checkpoints") in result
    assert ("loras", base / "loras") in result


def test_parse_extra_model_paths_multiline_value(tmp_path):
    """A ``key: |`` multi-line value yields one entry per non-blank line."""
    base = tmp_path / "alt"
    base.mkdir()
    (tmp_path / "extra_model_paths.yaml").write_text(
        f"""\
models:
    base_path: {base}
    text_encoders: |
        text_encoders/
        clip/
""",
        encoding="utf-8",
    )
    result = backend.parse_extra_model_paths(tmp_path)
    text_dirs = [d for t, d in result if t == "text_encoders"]
    assert base / "text_encoders" in text_dirs
    assert base / "clip" in text_dirs


def test_parse_extra_model_paths_multiple_sections(tmp_path):
    base1 = tmp_path / "first"
    base2 = tmp_path / "second"
    base1.mkdir()
    base2.mkdir()
    (tmp_path / "extra_model_paths.yaml").write_text(
        f"""\
models:
    base_path: {base1}
    checkpoints: checkpoints/

a1111:
    base_path: {base2}
    checkpoints: models/Stable-diffusion/
""",
        encoding="utf-8",
    )
    result = backend.parse_extra_model_paths(tmp_path)
    ckpt_dirs = [d for t, d in result if t == "checkpoints"]
    assert base1 / "checkpoints" in ckpt_dirs
    assert base2 / "models" / "Stable-diffusion" in ckpt_dirs


def test_parse_extra_model_paths_skips_section_without_base_path(tmp_path):
    (tmp_path / "extra_model_paths.yaml").write_text(
        """\
broken:
    checkpoints: somewhere/
""",
        encoding="utf-8",
    )
    assert backend.parse_extra_model_paths(tmp_path) == []


def test_parse_extra_model_paths_malformed_yaml_returns_empty(tmp_path):
    (tmp_path / "extra_model_paths.yaml").write_text(
        "not: [valid: yaml: at all", encoding="utf-8"
    )
    # Must not crash; return empty so check_models degrades to default path only.
    assert backend.parse_extra_model_paths(tmp_path) == []


def test_parse_extra_model_paths_skips_non_string_keys(tmp_path):
    """Section's non-`base_path` non-string entries (booleans, numbers) ignored."""
    base = tmp_path / "alt"
    base.mkdir()
    (tmp_path / "extra_model_paths.yaml").write_text(
        f"""\
models:
    base_path: {base}
    is_default: true
    checkpoints: checkpoints/
""",
        encoding="utf-8",
    )
    result = backend.parse_extra_model_paths(tmp_path)
    types = {t for t, _ in result}
    assert "is_default" not in types
    assert "checkpoints" in types


# ---------------------------------------------------------------------------
# find_model_path
# ---------------------------------------------------------------------------


def test_find_model_path_default_location(tmp_path):
    """File present in <COMFY_PATH>/models/ → reports default path."""
    target = tmp_path / "models" / "checkpoints" / "Illustrious"
    target.mkdir(parents=True)
    (target / "ILFlatMix.safetensors").write_bytes(b"\xff" * 100)

    path, present = backend.find_model_path(
        tmp_path, "checkpoints/Illustrious", "ILFlatMix.safetensors"
    )
    assert present is True
    assert path == target / "ILFlatMix.safetensors"


def test_find_model_path_extra_location(tmp_path):
    """File present in extra_model_paths location → reports that path."""
    extra_base = tmp_path / "extra"
    target = extra_base / "checkpoints" / "Illustrious"
    target.mkdir(parents=True)
    (target / "ILFlatMix.safetensors").write_bytes(b"\xff" * 100)

    (tmp_path / "extra_model_paths.yaml").write_text(
        f"""\
models:
    base_path: {extra_base}
    checkpoints: checkpoints/
""",
        encoding="utf-8",
    )
    path, present = backend.find_model_path(
        tmp_path, "checkpoints/Illustrious", "ILFlatMix.safetensors"
    )
    assert present is True
    assert path == target / "ILFlatMix.safetensors"


def test_find_model_path_zero_byte_treated_missing(tmp_path):
    target = tmp_path / "models" / "vae"
    target.mkdir(parents=True)
    (target / "vae.safetensors").write_bytes(b"")  # 0 bytes
    path, present = backend.find_model_path(
        tmp_path, "vae", "vae.safetensors"
    )
    assert present is False


def test_find_model_path_missing_everywhere_returns_default(tmp_path):
    """When file is missing in all candidates, full_path defaults to canonical loc."""
    extra = tmp_path / "extra"
    extra.mkdir()
    (tmp_path / "extra_model_paths.yaml").write_text(
        f"""\
models:
    base_path: {extra}
    loras: loras/
""",
        encoding="utf-8",
    )
    path, present = backend.find_model_path(
        tmp_path, "loras/qwen", "missing.safetensors"
    )
    assert present is False
    # Defaults to the in-repo canonical location for the user-friendly hint
    assert path == tmp_path / "models" / "loras" / "qwen" / "missing.safetensors"


def test_find_model_path_is_default_fallback(tmp_path):
    """Sections with ``is_default: true`` apply to ANY model type, even
    types not explicitly listed in the section. Real bug: user's YAML
    redirects checkpoints/loras/etc but leaves ultralytics/sams to fall
    through implicitly via ``is_default: true``."""
    extra = tmp_path / "alt"
    target = extra / "ultralytics" / "bbox"
    target.mkdir(parents=True)
    (target / "face_yolov8m.pt").write_bytes(b"\xff" * 100)
    (tmp_path / "extra_model_paths.yaml").write_text(
        f"""\
models:
    base_path: {extra}
    is_default: true
    checkpoints: checkpoints/
    loras: loras/
""",
        encoding="utf-8",
    )
    # Note: ultralytics is NOT explicitly listed, so the fallback rule
    # via is_default must kick in.
    path, present = backend.find_model_path(
        tmp_path, "ultralytics/bbox", "face_yolov8m.pt"
    )
    assert present is True
    assert path == target / "face_yolov8m.pt"


def test_parse_default_base_paths(tmp_path):
    base1 = tmp_path / "default_root"
    base2 = tmp_path / "non_default"
    (tmp_path / "extra_model_paths.yaml").write_text(
        f"""\
section_a:
    base_path: {base1}
    is_default: true
    checkpoints: checkpoints/

section_b:
    base_path: {base2}
    checkpoints: m/Stable-diffusion/
""",
        encoding="utf-8",
    )
    bases = backend.parse_default_base_paths(tmp_path)
    assert base1 in bases
    assert base2 not in bases


def test_find_model_path_subtree_under_extra_location(tmp_path):
    """REQUIRED_MODELS uses subdirs like 'loras/qwen/VNCCS' — must descend
    under the extra_model_paths-mapped base."""
    extra = tmp_path / "alt"
    deep = extra / "loras" / "qwen" / "VNCCS"
    deep.mkdir(parents=True)
    (deep / "EmotionCoreV1_000003000.safetensors").write_bytes(b"\xff" * 100)
    (tmp_path / "extra_model_paths.yaml").write_text(
        f"""\
models:
    base_path: {extra}
    loras: loras/
""",
        encoding="utf-8",
    )
    path, present = backend.find_model_path(
        tmp_path,
        "loras/qwen/VNCCS",
        "EmotionCoreV1_000003000.safetensors",
    )
    assert present is True
    assert path == deep / "EmotionCoreV1_000003000.safetensors"


# ---------------------------------------------------------------------------
# check_models integration
# ---------------------------------------------------------------------------


def test_check_models_finds_via_extra_model_paths(tmp_path, monkeypatch):
    """Build a fake comfy + extra_model_paths.yaml; one VNCCS-required model
    only exists in the extra location. check_models must find it."""
    fake_comfy = tmp_path / "ComfyUI"
    (fake_comfy / "custom_nodes").mkdir(parents=True)
    extra = tmp_path / "altmodels"
    (extra / "checkpoints" / "Illustrious").mkdir(parents=True)
    (extra / "checkpoints" / "Illustrious" / "ILFlatMix.safetensors").write_bytes(
        b"\xff" * 1024
    )
    (fake_comfy / "extra_model_paths.yaml").write_text(
        f"""\
models:
    base_path: {extra}
    checkpoints: checkpoints/
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    report = check_models.run_check_models()

    illustrious = next(
        r for r in report
        if r["filename"] == "ILFlatMix.safetensors"
    )
    assert illustrious["present"] is True
    assert "altmodels" in illustrious["full_path"]
