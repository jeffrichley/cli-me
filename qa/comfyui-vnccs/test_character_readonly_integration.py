"""Tier 2 integration tests for `character list` / `character show`.

Uses the `fake_comfy` fixture (per-test ComfyUI filesystem layout in
tmp_path) and extends it with a VNCCS state dir at the default location
(`<COMFY_PATH>/output/VN_CharacterCreatorSuit`). Runs the Typer
dispatcher through a `CliRunner` so we exercise stdout + exit codes
end-to-end.

No network: all filesystem state is in tmp_path. No ComfyUI server is
contacted (the READ-ONLY commands are pure filesystem).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

# conftest.py adds skill scripts/ to sys.path
from vnccs_cli import app as root_app
from vnccs_cli.backend import VNCCS_STATE_SUBDIR

pytestmark = pytest.mark.integration

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers — prepopulate the VNCCS state dir under a fake_comfy tree.
# ---------------------------------------------------------------------------


def _touch_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n")


def _state_root(fake_comfy: Path) -> Path:
    return fake_comfy / "output" / VNCCS_STATE_SUBDIR


def _make_empty_character(fake_comfy: Path, name: str) -> Path:
    """Character dir exists but has no Sheets/Faces/Sprites."""
    char = _state_root(fake_comfy) / name
    char.mkdir(parents=True, exist_ok=True)
    return char


def _make_full_character(fake_comfy: Path, name: str) -> Path:
    """Character with 2 costumes, 3 non-neutral emotions, sprites, dataset.

    Layout produced:
      {name}/
        {name}_config.json
        Sheets/
          Naked/neutral/sheet_neutral_00001_.png
          Casual/neutral/{v0..v3}.png
          Casual/happy/sheet_happy_00001_.png
          Casual/shy-blush/sheet_shy-blush_00001_.png
          Formal/neutral/v0.png
          Formal/angry/sheet_angry_00001_.png
        Sprites/Casual/neutral/sprite_neutral_0000{0,1}_.png
        lora/row_{0..1}.txt + .png
    """
    char = _state_root(fake_comfy) / name
    char.mkdir(parents=True, exist_ok=True)

    config = {
        "character_info": {"name": name, "sex": "female", "age": 20},
        "folder_structure": {
            "main_directories": ["Sprites", "Faces", "Sheets"],
            "emotions": ["neutral"],
        },
        "config_version": "2.0",
        "costumes": {
            "Naked": {},
            "Casual": {"top": "t-shirt", "picked_variant": "v2.png"},
            "Formal": {"top": "suit"},
        },
    }
    (char / f"{name}_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    # Base sheet
    _touch_png(char / "Sheets" / "Naked" / "neutral" / "sheet_neutral_00001_.png")

    # Casual costume: 4 variants, 2 non-neutral emotions
    for i in range(4):
        _touch_png(char / "Sheets" / "Casual" / "neutral" / f"v{i}.png")
    _touch_png(char / "Sheets" / "Casual" / "happy" / "sheet_happy_00001_.png")
    _touch_png(char / "Sheets" / "Casual" / "shy-blush" / "sheet_shy-blush_00001_.png")

    # Formal costume: 1 variant, 1 non-neutral emotion
    _touch_png(char / "Sheets" / "Formal" / "neutral" / "v0.png")
    _touch_png(char / "Sheets" / "Formal" / "angry" / "sheet_angry_00001_.png")

    # Sprites
    for i in range(2):
        _touch_png(
            char / "Sprites" / "Casual" / "neutral" / f"sprite_neutral_{i:05d}_.png"
        )

    # Dataset
    lora = char / "lora"
    lora.mkdir(parents=True, exist_ok=True)
    for i in range(2):
        (lora / f"row_{i}.txt").write_text("a caption", encoding="utf-8")
        _touch_png(lora / f"row_{i}.png")

    return char


# ---------------------------------------------------------------------------
# character list
# ---------------------------------------------------------------------------


class TestCharacterListIntegration:
    def test_zero_characters_reports_and_exits_zero(self, fake_comfy, monkeypatch):
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        # State root does not exist yet — the command must NOT error.
        result = runner.invoke(root_app, ["character", "list"])
        assert result.exit_code == 0, result.stderr
        assert "No characters found" in result.stdout

    def test_rich_table_lists_both_characters(self, fake_comfy, monkeypatch):
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        _make_empty_character(fake_comfy, "Empty")
        _make_full_character(fake_comfy, "Alina")

        result = runner.invoke(root_app, ["character", "list"])
        assert result.exit_code == 0, result.stderr
        # Both names appear; Alina's sheets-subdir walk reports 3 costumes
        # (Naked + Casual + Formal) and some emotion total > 0.
        assert "Alina" in result.stdout
        assert "Empty" in result.stdout

    def test_json_output_structure(self, fake_comfy, monkeypatch):
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        _make_empty_character(fake_comfy, "Empty")
        _make_full_character(fake_comfy, "Alina")

        result = runner.invoke(root_app, ["character", "list", "--json"])
        assert result.exit_code == 0, result.stderr
        data = json.loads(result.stdout)
        by_name = {c["name"]: c for c in data}
        assert set(by_name) == {"Alina", "Empty"}

        alina = by_name["Alina"]
        # 3 costume dirs under Sheets: Naked, Casual, Formal.
        assert alina["costume_count"] == 3
        # Emotions summed across costumes: Naked/neutral + Casual/{neutral,
        # happy, shy-blush} + Formal/{neutral, angry} = 1 + 3 + 2 = 6.
        assert alina["emotion_count"] == 6

        empty = by_name["Empty"]
        assert empty["costume_count"] == 0
        assert empty["emotion_count"] == 0

    def test_state_dir_flag_overrides(self, fake_comfy, tmp_path, monkeypatch):
        """--state-dir flag takes precedence over COMFY_PATH default."""
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
        # COMFY_PATH default state dir exists (empty) — but we override
        # to a different root with one character, and expect only that one.
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        _make_full_character(fake_comfy, "Decoy")  # in default loc

        other_state = tmp_path / "other_state"
        other_state.mkdir()
        (other_state / "OtherChar").mkdir()

        result = runner.invoke(
            root_app, ["character", "list", "--state-dir", str(other_state), "--json"]
        )
        assert result.exit_code == 0, result.stderr
        data = json.loads(result.stdout)
        names = {c["name"] for c in data}
        assert names == {"OtherChar"}


# ---------------------------------------------------------------------------
# character show
# ---------------------------------------------------------------------------


class TestCharacterShowIntegration:
    def test_nonexistent_exits_5(self, fake_comfy, monkeypatch):
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        result = runner.invoke(root_app, ["character", "show", "NONEXISTENT"])
        assert result.exit_code == 5
        # Error message should reference the name so the user can fix the typo.
        assert "NONEXISTENT" in (result.stderr or "") + result.stdout

    def test_full_character_json(self, fake_comfy, monkeypatch):
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        _make_full_character(fake_comfy, "Alina")

        result = runner.invoke(
            root_app, ["character", "show", "Alina", "--json"]
        )
        assert result.exit_code == 0, result.stderr
        rec = json.loads(result.stdout)

        assert rec["name"] == "Alina"
        assert rec["config"]["present"] is True
        assert rec["character_sheet"]["present"] is True
        assert rec["character_sheet"]["size"] > 0

        by_name = {c["name"]: c for c in rec["costumes"]}
        assert set(by_name) == {"Naked", "Casual", "Formal"}
        # 4 v*.png; no neutral sheet in Casual/neutral/ from fixture.
        assert by_name["Casual"]["variant_count"] == 4
        assert by_name["Casual"]["picked_variant"] == "v2.png"
        # 1 v*.png in Formal/neutral/.
        assert by_name["Formal"]["variant_count"] == 1
        # Naked/neutral/ contains the base sheet (sheet_neutral_00001_.png)
        # which counts as a variant PNG under the costume walker.
        assert by_name["Naked"]["variant_count"] == 1

        emo_keys = {(e["costume"], e["emotion_type"]) for e in rec["emotions"]}
        assert ("Casual", "happy") in emo_keys
        assert ("Casual", "shy-blush") in emo_keys
        assert ("Formal", "angry") in emo_keys
        # neutral must never appear in the emotions block.
        assert all(e["emotion_type"] != "neutral" for e in rec["emotions"])

        assert rec["sprites"]["exists"] is True
        assert rec["sprites"]["png_count"] == 2

        assert rec["dataset"]["exists"] is True
        assert rec["dataset"]["row_count"] == 2

    def test_empty_character_show_tolerates_missing_artifacts(
        self, fake_comfy, monkeypatch
    ):
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        _make_empty_character(fake_comfy, "Empty")

        result = runner.invoke(
            root_app, ["character", "show", "Empty", "--json"]
        )
        assert result.exit_code == 0, result.stderr
        rec = json.loads(result.stdout)
        assert rec["config"]["present"] is False
        assert rec["character_sheet"]["present"] is False
        assert rec["costumes"] == []
        assert rec["emotions"] == []
        assert rec["sprites"]["exists"] is False
        assert rec["dataset"]["exists"] is False

    def test_rich_output_shows_core_fields(self, fake_comfy, monkeypatch):
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        _make_full_character(fake_comfy, "Alina")

        result = runner.invoke(root_app, ["character", "show", "Alina"])
        assert result.exit_code == 0, result.stderr
        # Structural assertions — tolerant of column widths / Rich styling.
        assert "Alina" in result.stdout
        assert "Casual" in result.stdout
        assert "happy" in result.stdout
