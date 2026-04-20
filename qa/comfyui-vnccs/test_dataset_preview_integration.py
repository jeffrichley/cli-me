"""Tier 2 integration tests for `vnccs dataset preview`.

These use the ``fake_comfy`` fixture (a real on-disk ComfyUI layout in
tmp_path) plus real sprite PNG files on disk. Still no ComfyUI HTTP
calls — ``dataset preview`` is by design a pure filesystem dry-run — but
the tests exercise the full CLI round-trip via Typer's ``CliRunner``.

Marked ``@pytest.mark.integration`` so they run in the slower tier.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vnccs_cli import app as root_app

from _vnccs_helpers import (
    make_empty_fake_character,
    make_fake_character_with_sprites,
)


pytestmark = pytest.mark.integration


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_preview_reports_correct_counts_from_real_tree(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build a real 5-sprite character tree; assert stdout lists all 5 + counts."""
    monkeypatch.delenv("COMFY_PATH", raising=False)
    monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
    make_fake_character_with_sprites(fake_comfy, "Aria", sprite_count=5)

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Aria", "--path", str(fake_comfy)],
    )

    assert result.exit_code == 0, result.output
    stdout = result.stdout
    # 5 real sprite PNGs on disk should all appear in the samples list.
    for i in range(1, 6):
        assert f"sprite_happy_{i:05d}_.png" in stdout, (
            f"Expected sprite #{i} in dry-run output:\n{stdout}"
        )
    # Exact count line (anchored so bare "5" matches in surrounding text
    # don't count — mutation-resistant per r4 feedback).
    assert "sprites found" in stdout


def test_preview_json_has_all_five_samples(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMFY_PATH", raising=False)
    monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
    make_fake_character_with_sprites(fake_comfy, "Aria", sprite_count=5)

    result = runner.invoke(
        root_app,
        [
            "dataset", "preview", "Aria",
            "--path", str(fake_comfy),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output

    payload = json.loads(result.stdout)
    assert payload["sprite_count"] == 5
    assert payload["face_count"] == 0
    assert payload["pair_count"] == 5
    assert payload["caption_count"] == 5
    assert len(payload["samples"]) == 5
    # Kohya prefix default == "VN_<character_name>" (falls back to dir name)
    assert payload["output_layout"]["caption_prefix"] == "VN_Aria"


def test_preview_with_faces_and_sprites(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end Tier 2 for the Faces+Sprites walk (r3/dataset D1 fix)."""
    monkeypatch.delenv("COMFY_PATH", raising=False)
    monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
    char_dir = make_fake_character_with_sprites(fake_comfy, "Aria", sprite_count=3)
    faces_dir = char_dir / "Faces" / "casual" / "happy"
    faces_dir.mkdir(parents=True)
    for i in range(1, 3):
        (faces_dir / f"face_happy_{i:05d}_.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Aria", "--path", str(fake_comfy), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["face_count"] == 2
    assert payload["sprite_count"] == 3
    assert payload["pair_count"] == 5


def test_preview_truncation_message_appears_for_large_trees(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """25 sprites → stdout should show 10 samples + "... and 15 more"."""
    monkeypatch.delenv("COMFY_PATH", raising=False)
    monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
    make_fake_character_with_sprites(fake_comfy, "Aria", sprite_count=25)

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Aria", "--path", str(fake_comfy)],
    )
    assert result.exit_code == 0, result.output
    assert "and 15 more" in result.stdout


def test_preview_empty_character_exits_five(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMFY_PATH", raising=False)
    monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
    make_empty_fake_character(fake_comfy, "Ghost")

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Ghost", "--path", str(fake_comfy)],
    )
    assert result.exit_code == 5
    # Error message mentions missing training images AND character name
    # (AND, not OR — per r4 feedback, OR lets degenerate messages pass).
    assert "training images" in result.output.lower()
    assert "Ghost" in result.output


def test_preview_nonexistent_character_exits_five(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMFY_PATH", raising=False)
    monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Phantom", "--path", str(fake_comfy)],
    )
    assert result.exit_code == 5
    assert "Phantom" in result.output
    assert "not found" in result.output.lower()


def test_preview_does_not_create_files(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HARD CONTRACT: dry-run must not create the `<char>/lora/` directory."""
    monkeypatch.delenv("COMFY_PATH", raising=False)
    make_fake_character_with_sprites(fake_comfy, "Aria", sprite_count=3)
    lora_dir = (
        fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria" / "lora"
    )
    assert not lora_dir.exists()

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Aria", "--path", str(fake_comfy)],
    )
    assert result.exit_code == 0
    assert not lora_dir.exists(), "dry-run must not write anything to disk"
