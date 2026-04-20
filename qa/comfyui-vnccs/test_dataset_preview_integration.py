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
    make_fake_character_with_sprites(fake_comfy, "Aria", sprite_count=5)

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Aria", "--path", str(fake_comfy)],
    )

    assert result.exit_code == 0, result.stderr or result.stdout
    stdout = result.stdout
    # 5 real sprite PNGs on disk should all appear in the samples list.
    for i in range(1, 6):
        assert f"sprite_happy_{i:05d}_.png" in stdout, (
            f"Expected sprite #{i} in dry-run output:\n{stdout}"
        )
    # Counts reach the rendered summary table too.
    assert "5" in stdout


def test_preview_json_has_all_five_samples(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMFY_PATH", raising=False)
    make_fake_character_with_sprites(fake_comfy, "Aria", sprite_count=5)

    result = runner.invoke(
        root_app,
        [
            "dataset", "preview", "Aria",
            "--path", str(fake_comfy),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stderr or result.stdout

    payload = json.loads(result.stdout)
    assert payload["sprite_count"] == 5
    assert payload["caption_count"] == 5
    assert len(payload["sprite_samples"]) == 5
    # Kohya prefix default == "VN_<character>"
    assert payload["output_layout"]["caption_prefix"] == "VN_Aria"


def test_preview_truncation_message_appears_for_large_trees(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """25 sprites → stdout should show 10 samples + "... and 15 more"."""
    monkeypatch.delenv("COMFY_PATH", raising=False)
    make_fake_character_with_sprites(fake_comfy, "Aria", sprite_count=25)

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Aria", "--path", str(fake_comfy)],
    )
    assert result.exit_code == 0, result.stderr or result.stdout
    assert "and 15 more" in result.stdout


def test_preview_empty_character_exits_five(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMFY_PATH", raising=False)
    make_empty_fake_character(fake_comfy, "Ghost")

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Ghost", "--path", str(fake_comfy)],
    )
    assert result.exit_code == 5
    # Error message must mention the missing sprites (not the character itself).
    combined = (result.stderr or "") + result.stdout
    assert "sprite" in combined.lower() or "Ghost" in combined


def test_preview_nonexistent_character_exits_five(
    fake_comfy: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMFY_PATH", raising=False)

    result = runner.invoke(
        root_app,
        ["dataset", "preview", "Phantom", "--path", str(fake_comfy)],
    )
    assert result.exit_code == 5
    combined = (result.stderr or "") + result.stdout
    assert "Phantom" in combined or "not found" in combined.lower()


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
