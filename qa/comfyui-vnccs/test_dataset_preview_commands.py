"""Tier 1 tests for `vnccs dataset preview` — mocked filesystem.

Fast, hermetic checks of the logic layer (``commands/dataset_preview.py``).
Uses ``tmp_path`` to build minimal fake filesystem trees rather than
stubbing ``Path.glob`` / ``iterdir`` directly — the real filesystem IS
the data under test for a dry-run command, and monkeypatching Path
methods is brittle against the real implementation.

No ComfyUI HTTP calls (the command is a pure dry-run). No network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

# conftest.py adds skill scripts/ to sys.path.
from vnccs_cli import app as root_app
from vnccs_cli.backend import VnccsNotFoundError, VnccsPathError
from vnccs_cli.commands import dataset_preview

from _vnccs_helpers import (
    make_empty_fake_character,
    make_fake_character_with_sprites,
)


pytestmark = pytest.mark.command_graph


# ---------------------------------------------------------------------------
# run_preview — the logic layer directly
# ---------------------------------------------------------------------------


class TestRunPreviewHappyPath:
    def test_returns_expected_shape_and_counts(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        make_fake_character_with_sprites(comfy, "Aria", sprite_count=5)

        result = dataset_preview.run_preview(
            "Aria", comfy_path=str(comfy)
        )

        assert result["character"] == "Aria"
        assert result["game_name"] == "VN"  # default
        assert result["sprite_count"] == 5
        # 1:1 caption/sprite per DatasetGenerator contract
        assert result["caption_count"] == result["sprite_count"]
        assert result["total_samples"] == 5
        assert len(result["sprite_samples"]) == 5

    def test_game_name_flows_into_layout_and_prefix(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        make_fake_character_with_sprites(comfy, "Aria", sprite_count=3)

        result = dataset_preview.run_preview(
            "Aria", game_name="MyVN", comfy_path=str(comfy)
        )

        assert result["game_name"] == "MyVN"
        # kohya caption-prefix convention: <game>_<character>
        assert result["output_layout"]["caption_prefix"] == "MyVN_Aria"

    def test_sample_list_truncates_to_ten(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        make_fake_character_with_sprites(comfy, "Aria", sprite_count=25)

        result = dataset_preview.run_preview("Aria", comfy_path=str(comfy))

        assert result["sprite_count"] == 25
        assert result["total_samples"] == 25
        # Samples capped at SAMPLE_LIMIT so the table/JSON stays compact.
        assert len(result["sprite_samples"]) == dataset_preview.SAMPLE_LIMIT == 10

    def test_multiple_costumes_and_emotions_aggregate(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        # 5 sprites in casual/happy, + 1 in casual/sad, + 1 in casual/angry
        make_fake_character_with_sprites(
            comfy,
            "Aria",
            sprite_count=5,
            extra_emotions=["sad", "angry"],
        )

        result = dataset_preview.run_preview("Aria", comfy_path=str(comfy))
        assert result["sprite_count"] == 7

    def test_non_sprite_files_are_ignored(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        char_dir = make_fake_character_with_sprites(
            comfy, "Aria", sprite_count=3
        )
        # Stray non-sprite files must not inflate the count (matches
        # DatasetGenerator.generate_dataset filter).
        emotion_dir = char_dir / "Sprites" / "casual" / "happy"
        (emotion_dir / "thumb.txt").write_text("not a sprite", encoding="utf-8")
        (emotion_dir / "face_happy_00001_.png").write_bytes(b"\x89PNG")
        (emotion_dir / "sprite_happy_99999_.txt").write_text("stray txt", encoding="utf-8")

        result = dataset_preview.run_preview("Aria", comfy_path=str(comfy))
        assert result["sprite_count"] == 3


# ---------------------------------------------------------------------------
# run_preview — error branches
# ---------------------------------------------------------------------------


class TestRunPreviewErrors:
    def test_missing_character_raises_not_found(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")

        with pytest.raises(VnccsNotFoundError) as exc:
            dataset_preview.run_preview("Nobody", comfy_path=str(comfy))

        assert "Nobody" in exc.value.message
        assert exc.value.exit_code == 5

    def test_character_with_no_sprites_raises_not_found(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        make_empty_fake_character(comfy, "Ghost")

        with pytest.raises(VnccsNotFoundError) as exc:
            dataset_preview.run_preview("Ghost", comfy_path=str(comfy))

        assert "sprites" in exc.value.message.lower()
        assert exc.value.exit_code == 5

    def test_character_with_only_non_sprite_files_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        char = comfy / "output" / "VN_CharacterCreatorSuit" / "Empty"
        emotion_dir = char / "Sprites" / "casual" / "happy"
        emotion_dir.mkdir(parents=True)
        (emotion_dir / "face_happy_00001_.png").write_bytes(b"\x89PNG")

        with pytest.raises(VnccsNotFoundError):
            dataset_preview.run_preview("Empty", comfy_path=str(comfy))

    def test_unset_comfy_path_raises_path_error(self, clean_env):
        # clean_env clears COMFY_PATH & COMFY_URL.
        with pytest.raises(VnccsPathError) as exc:
            dataset_preview.run_preview("Aria")
        assert exc.value.exit_code == 6


# ---------------------------------------------------------------------------
# format_json — JSON contract shape
# ---------------------------------------------------------------------------


class TestFormatJson:
    def test_shape_is_stable(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        make_fake_character_with_sprites(comfy, "Aria", sprite_count=2)

        result = dataset_preview.run_preview("Aria", comfy_path=str(comfy))
        text = dataset_preview.format_json(result)
        parsed = json.loads(text)

        # Documented contract — reviewers pin this shape.
        assert set(parsed.keys()) == {
            "character",
            "sprite_count",
            "caption_count",
            "output_layout",
            "sprite_samples",
        }
        assert parsed["character"] == "Aria"
        assert parsed["sprite_count"] == 2
        assert isinstance(parsed["sprite_samples"], list)


# ---------------------------------------------------------------------------
# CLI dispatch — typer layer (round-trip via CliRunner)
# ---------------------------------------------------------------------------


class TestCliDispatch:
    runner = CliRunner()

    def test_preview_command_runs_and_exits_zero(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        make_fake_character_with_sprites(comfy, "Aria", sprite_count=4)

        result = self.runner.invoke(
            root_app,
            ["dataset", "preview", "Aria", "--path", str(comfy)],
        )
        assert result.exit_code == 0, result.stderr or result.stdout
        assert "Aria" in result.stdout

    def test_preview_json_flag_emits_parseable_json(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        make_fake_character_with_sprites(comfy, "Aria", sprite_count=4)

        result = self.runner.invoke(
            root_app,
            ["dataset", "preview", "Aria", "--path", str(comfy), "--json"],
        )
        assert result.exit_code == 0, result.stderr or result.stdout
        payload = json.loads(result.stdout)
        assert payload["character"] == "Aria"
        assert payload["sprite_count"] == 4
        assert payload["caption_count"] == 4

    def test_preview_game_name_flows_into_json(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        make_fake_character_with_sprites(comfy, "Aria", sprite_count=1)

        result = self.runner.invoke(
            root_app,
            [
                "dataset", "preview", "Aria",
                "--path", str(comfy),
                "--game-name", "MyVN",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.stderr or result.stdout
        payload = json.loads(result.stdout)
        assert payload["output_layout"]["caption_prefix"] == "MyVN_Aria"

    def test_preview_missing_character_exits_five(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")

        result = self.runner.invoke(
            root_app,
            ["dataset", "preview", "Nobody", "--path", str(comfy)],
        )
        assert result.exit_code == 5

    def test_preview_empty_character_exits_five(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        make_empty_fake_character(comfy, "Ghost")

        result = self.runner.invoke(
            root_app,
            ["dataset", "preview", "Ghost", "--path", str(comfy)],
        )
        assert result.exit_code == 5


# ---------------------------------------------------------------------------
# Helpers local to this module
# ---------------------------------------------------------------------------


def _make_fake_comfy(root: Path) -> Path:
    """Minimal fake ComfyUI install; duplicates conftest's helper so this
    file can be invoked standalone without needing the ``fake_comfy``
    fixture (the fixture returns the root pre-built; these tests want to
    customize its contents before running the command)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "custom_nodes").mkdir(exist_ok=True)
    (root / "models").mkdir(exist_ok=True)
    (root / "output").mkdir(exist_ok=True)
    (root / "main.py").write_text("# fake comfy\n", encoding="utf-8")
    return root
