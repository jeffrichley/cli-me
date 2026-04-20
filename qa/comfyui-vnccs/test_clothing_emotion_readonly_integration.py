"""Tier 2 (filesystem integration) tests for read-only clothing + emotion commands.

These tests exercise the full Typer CLI via ``CliRunner`` against a
``fake_comfy`` filesystem tree — no ComfyUI process, no HTTP calls, but
a full end-to-end run of the command pipeline (typer -> logic layer ->
Path walks -> renderer). This catches regressions the mocked Tier 1
tests can miss (JSON-shape bugs, Rich-table column ordering, argv
wiring).

State layout assumption: ``<comfy>/output/VN_CharacterCreatorSuit/
<character>/...`` per ``references/source-analysis/state-management.md``.
One character, 2 costumes (3 variants + 1 picked), 3 emotions per
costume — sized per the Wave 1 spec.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

# conftest.py adds skill scripts/ to sys.path, and qa dir to sys.path
from _vnccs_helpers import (
    make_fake_costumes_dir,
    make_fake_emotion_preview,
)
from vnccs_cli import app as root_app

pytestmark = pytest.mark.integration


CHARACTER = "Alina"
COSTUMES = {
    "casual": {"variants": 3, "picked": 2, "top": "t-shirt", "bottom": "jeans"},
    "formal": {"variants": 1, "picked": None, "top": "blouse"},
}
EMOTIONS = ("happy", "sad", "angry")


@pytest.fixture
def populated_comfy(fake_comfy, monkeypatch):
    """Fake ComfyUI with one character, 2 costumes, 3 emotions each."""
    make_fake_costumes_dir(
        fake_comfy,
        CHARACTER,
        costumes=COSTUMES,
        emotions=EMOTIONS,
    )
    # Bundle a preview for 'angry' — the 'happy' / 'sad' previews intentionally
    # absent so we can test the "unknown emotion" preview branch on real state.
    make_fake_emotion_preview(fake_comfy, emotion="angry")
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    monkeypatch.delenv("COMFY_URL", raising=False)
    return fake_comfy


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# clothing list
# ---------------------------------------------------------------------------


class TestClothingListIntegration:
    def test_single_character_json(self, populated_comfy, runner):
        result = runner.invoke(root_app, ["clothing","list", CHARACTER, "--json"])
        assert result.exit_code == 0, result.stdout
        rows = json.loads(result.stdout)
        by_costume = {r["costume"]: r for r in rows}
        assert "Naked" in by_costume
        assert by_costume["casual"]["variant_count"] == 3
        assert by_costume["casual"]["picked_variant"] == 2
        assert by_costume["formal"]["variant_count"] == 1
        assert by_costume["formal"]["picked_variant"] is None

    def test_single_character_table(self, populated_comfy, runner):
        result = runner.invoke(root_app, ["clothing","list", CHARACTER])
        assert result.exit_code == 0, result.stdout
        assert CHARACTER in result.stdout
        assert "casual" in result.stdout
        assert "formal" in result.stdout
        # Picked=2 appears; unpicked rendered as dash.
        assert "2" in result.stdout
        assert "—" in result.stdout

    def test_all_characters_json(self, populated_comfy, runner):
        result = runner.invoke(root_app, ["clothing","list", "--json"])
        assert result.exit_code == 0, result.stdout
        rows = json.loads(result.stdout)
        assert all(r["character"] == CHARACTER for r in rows)
        assert {r["costume"] for r in rows} >= {"Naked", "casual", "formal"}

    def test_unknown_character_exits_5(self, populated_comfy, runner):
        result = runner.invoke(root_app, ["clothing","list", "DoesNotExist"])
        assert result.exit_code == 5

    def test_empty_state_root_prints_empty(self, fake_comfy, runner, monkeypatch):
        # No characters created at all.
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        result = runner.invoke(root_app, ["clothing","list"])
        assert result.exit_code == 0
        assert "No costumes found" in result.stdout


# ---------------------------------------------------------------------------
# emotion list
# ---------------------------------------------------------------------------


class TestEmotionListIntegration:
    def test_rows_cover_all_costume_emotion_pairs(self, populated_comfy, runner):
        result = runner.invoke(root_app, ["emotion","list", CHARACTER, "--json"])
        assert result.exit_code == 0, result.stdout
        rows = json.loads(result.stdout)
        pairs = {(r["costume"], r["emotion"]) for r in rows}
        for costume in COSTUMES:
            # neutral gets sheet_neutral_NNNNN_.png from the variants helper
            assert (costume, "neutral") in pairs
            for emotion in EMOTIONS:
                assert (costume, emotion) in pairs

    def test_table_renders(self, populated_comfy, runner):
        result = runner.invoke(root_app, ["emotion","list", CHARACTER])
        assert result.exit_code == 0, result.stdout
        for emotion in EMOTIONS:
            assert emotion in result.stdout

    def test_unknown_character_exits_5(self, populated_comfy, runner):
        result = runner.invoke(root_app, ["emotion","list", "DoesNotExist"])
        assert result.exit_code == 5


# ---------------------------------------------------------------------------
# emotion show
# ---------------------------------------------------------------------------


class TestEmotionShowIntegration:
    def test_show_with_costume(self, populated_comfy, runner):
        result = runner.invoke(
            root_app,
            ["emotion", "show", CHARACTER, "--emotion", "happy", "--costume", "casual", "--json"],
        )
        assert result.exit_code == 0, result.stdout
        info = json.loads(result.stdout)
        assert info["character"] == CHARACTER
        assert info["costume"] == "casual"
        assert info["emotion"] == "happy"
        assert Path(info["path"]).name == "sheet_happy_00001_.png"
        assert info["size"] > 0
        assert info["created"]  # any non-empty ISO-ish string

    def test_ambiguous_without_costume_exits_5(self, populated_comfy, runner):
        # 'happy' exists in both casual and formal → ambiguous.
        result = runner.invoke(
            root_app, ["emotion", "show", CHARACTER, "--emotion", "happy"]
        )
        assert result.exit_code == 5

    def test_unknown_character_exits_5(self, populated_comfy, runner):
        result = runner.invoke(
            root_app,
            ["emotion", "show", "DoesNotExist", "--emotion", "happy"],
        )
        assert result.exit_code == 5

    def test_unknown_emotion_exits_5(self, populated_comfy, runner):
        result = runner.invoke(
            root_app,
            ["emotion", "show", CHARACTER, "--emotion", "never-rendered", "--costume", "casual"],
        )
        assert result.exit_code == 5

    def test_show_renders_table(self, populated_comfy, runner):
        result = runner.invoke(
            root_app,
            ["emotion", "show", CHARACTER, "--emotion", "sad", "--costume", "casual"],
        )
        assert result.exit_code == 0, result.stdout
        assert "sad" in result.stdout
        assert "casual" in result.stdout
        assert "sheet_sad_00001_.png" in result.stdout


# ---------------------------------------------------------------------------
# emotion preview
# ---------------------------------------------------------------------------


class TestEmotionPreviewIntegration:
    def test_known_emotion_plaintext(self, populated_comfy, runner):
        result = runner.invoke(
            root_app, ["emotion", "preview", CHARACTER, "--emotion", "angry"]
        )
        assert result.exit_code == 0, result.stdout
        # stdout should be just the absolute path, trimmed.
        printed = result.stdout.strip()
        assert printed.endswith("angry.png")
        assert Path(printed).exists()

    def test_known_emotion_json(self, populated_comfy, runner):
        result = runner.invoke(
            root_app,
            ["emotion", "preview", CHARACTER, "--emotion", "angry", "--json"],
        )
        assert result.exit_code == 0, result.stdout
        info = json.loads(result.stdout)
        assert info["emotion"] == "angry"
        assert info["exists"] is True
        assert info["path"].endswith("angry.png")

    def test_unknown_emotion_exits_5(self, populated_comfy, runner):
        result = runner.invoke(
            root_app, ["emotion", "preview", CHARACTER, "--emotion", "bogus"]
        )
        assert result.exit_code == 5

    def test_unknown_character_exits_5(self, populated_comfy, runner):
        result = runner.invoke(
            root_app, ["emotion", "preview", "Nobody", "--emotion", "angry"]
        )
        assert result.exit_code == 5
