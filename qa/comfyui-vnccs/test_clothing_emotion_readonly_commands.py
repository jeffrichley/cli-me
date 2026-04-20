"""Tier 1 (mocked) tests for read-only clothing + emotion commands.

Exercises the logic layer (`commands.clothing_list`, `commands.emotion_list`,
`commands.emotion_show`, `commands.emotion_preview`) directly — no
subprocess, no real ComfyUI needed. Filesystem is reached via `tmp_path`
and/or `unittest.mock.patch.object(Path, ...)` — no network.

Every command gets a kitchen-sink test that walks every flag and every
major branch (character given / omitted, `--json` / no-json, not-found).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

# conftest.py adds skill scripts/ to sys.path, and qa dir to sys.path
from _vnccs_helpers import (
    make_empty_fake_character,
    make_fake_costumes_dir,
    make_fake_emotion_preview,
)
from vnccs_cli import app as root_app
from vnccs_cli.backend import VnccsNotFoundError, VnccsPathError
from vnccs_cli.commands import (
    clothing_list,
    emotion_list,
    emotion_preview,
    emotion_show,
)


# ---------------------------------------------------------------------------
# clothing list — logic
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestClothingListLogic:
    def test_unset_comfy_path_raises(self, clean_env):
        with pytest.raises(VnccsPathError) as exc:
            clothing_list.run_list()
        assert exc.value.exit_code == 6

    def test_character_not_found_raises(self, clean_env, fake_comfy):
        with pytest.raises(VnccsNotFoundError) as exc:
            clothing_list.run_list("Nobody", comfy_path=str(fake_comfy))
        assert exc.value.exit_code == 5
        assert "Nobody" in exc.value.message

    def test_all_characters_missing_state_root_returns_empty(self, clean_env, fake_comfy):
        # fake_comfy has custom_nodes/output/etc., but no
        # VN_CharacterCreatorSuit subdir — should be an empty list, not error.
        assert clothing_list.run_list(comfy_path=str(fake_comfy)) == []

    def test_single_character_rows(self, clean_env, fake_comfy):
        make_fake_costumes_dir(
            fake_comfy,
            "Alina",
            costumes={"casual": {"variants": 3, "picked": 2}},
            emotions=("happy",),
        )
        rows = clothing_list.run_list("Alina", comfy_path=str(fake_comfy))
        names = {r["costume"] for r in rows}
        # Naked always included, plus the costume we declared.
        assert "Naked" in names
        assert "casual" in names
        casual = next(r for r in rows if r["costume"] == "casual")
        assert casual["character"] == "Alina"
        assert casual["variant_count"] == 3
        assert casual["picked_variant"] == 2

    def test_picked_none_when_unpicked(self, clean_env, fake_comfy):
        make_fake_costumes_dir(
            fake_comfy,
            "Alina",
            costumes={"formal": {"variants": 1, "picked": None}},
            emotions=(),
        )
        rows = clothing_list.run_list("Alina", comfy_path=str(fake_comfy))
        formal = next(r for r in rows if r["costume"] == "formal")
        assert formal["picked_variant"] is None

    def test_all_characters_mode_aggregates(self, clean_env, fake_comfy):
        make_fake_costumes_dir(
            fake_comfy,
            "Alina",
            costumes={"casual": {"variants": 2, "picked": None}},
            emotions=(),
        )
        make_fake_costumes_dir(
            fake_comfy,
            "Bob",
            costumes={"formal": {"variants": 1, "picked": 1}},
            emotions=(),
        )
        rows = clothing_list.run_list(comfy_path=str(fake_comfy))
        characters_seen = {r["character"] for r in rows}
        assert characters_seen == {"Alina", "Bob"}

    def test_variant_count_zero_for_costume_without_neutral_dir(self, clean_env, fake_comfy):
        # Costume declared in config but no Sheets/<costume>/neutral/ on disk.
        char_dir = fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Alina"
        char_dir.mkdir(parents=True)
        (char_dir / "Alina_config.json").write_text(
            json.dumps({"costumes": {"ghost": {}}}),
            encoding="utf-8",
        )
        rows = clothing_list.run_list("Alina", comfy_path=str(fake_comfy))
        ghost = next(r for r in rows if r["costume"] == "ghost")
        assert ghost["variant_count"] == 0
        assert ghost["picked_variant"] is None

    def test_malformed_config_treated_as_empty(self, clean_env, fake_comfy):
        char_dir = fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Alina"
        char_dir.mkdir(parents=True)
        (char_dir / "Alina_config.json").write_text("{not valid json", encoding="utf-8")
        # Should not raise; Naked still present.
        rows = clothing_list.run_list("Alina", comfy_path=str(fake_comfy))
        assert any(r["costume"] == "Naked" for r in rows)


@pytest.mark.command_graph
class TestClothingListCli:
    """Kitchen-sink coverage of the typer wrapper for `clothing list`."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_exits_zero_with_no_results(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        with patch.object(clothing_list, "run_list", return_value=[]):
            result = self.runner.invoke(root_app, ["clothing","list"])
        assert result.exit_code == 0
        assert "No costumes found" in result.stdout

    def test_renders_table_with_rows(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        fake_rows = [
            {"character": "Alina", "costume": "Naked", "variant_count": 0, "picked_variant": None},
            {"character": "Alina", "costume": "casual", "variant_count": 3, "picked_variant": 2},
        ]
        with patch.object(clothing_list, "run_list", return_value=fake_rows):
            result = self.runner.invoke(root_app, ["clothing","list", "Alina"])
        assert result.exit_code == 0
        assert "Alina" in result.stdout
        assert "casual" in result.stdout
        # Dash placeholder for the unpicked Naked row.
        assert "—" in result.stdout

    def test_json_flag_emits_json(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        fake_rows = [
            {"character": "Alina", "costume": "casual", "variant_count": 1, "picked_variant": None},
        ]
        with patch.object(clothing_list, "run_list", return_value=fake_rows):
            result = self.runner.invoke(root_app, ["clothing","list", "Alina", "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert parsed == fake_rows

    def test_character_omitted_uses_all_mode(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        fake_rows = [
            {"character": "Alina", "costume": "Naked", "variant_count": 0, "picked_variant": None},
            {"character": "Bob", "costume": "Naked", "variant_count": 0, "picked_variant": None},
        ]
        with patch.object(clothing_list, "run_list", return_value=fake_rows) as m:
            result = self.runner.invoke(root_app, ["clothing","list"])
        assert result.exit_code == 0
        # First positional arg to run_list is `None` when character is omitted.
        call_args, call_kwargs = m.call_args
        assert call_args == (None,) or call_kwargs.get("character") is None

    def test_not_found_exits_five(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        err = VnccsNotFoundError("Character not found: 'Nope'")
        with patch.object(clothing_list, "run_list", side_effect=err):
            result = self.runner.invoke(root_app, ["clothing","list", "Nope"])
        assert result.exit_code == 5

    def test_path_flag_forwarded(self, monkeypatch, tmp_path):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        with patch.object(clothing_list, "run_list", return_value=[]) as m:
            result = self.runner.invoke(
                root_app, ["clothing", "list", "--path", str(tmp_path / "somepath")]
            )
        assert result.exit_code == 0
        _, call_kwargs = m.call_args
        assert call_kwargs["comfy_path"] == str(tmp_path / "somepath")


# ---------------------------------------------------------------------------
# emotion list — logic
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestEmotionListLogic:
    def test_unset_comfy_path_raises(self, clean_env):
        with pytest.raises(VnccsPathError) as exc:
            emotion_list.run_list("Alina")
        assert exc.value.exit_code == 6

    def test_character_not_found_raises(self, clean_env, fake_comfy):
        with pytest.raises(VnccsNotFoundError) as exc:
            emotion_list.run_list("Nobody", comfy_path=str(fake_comfy))
        assert exc.value.exit_code == 5

    def test_no_sheets_dir_returns_empty(self, clean_env, fake_comfy):
        make_empty_fake_character(fake_comfy, "Alina")
        assert emotion_list.run_list("Alina", comfy_path=str(fake_comfy)) == []

    def test_rows_include_every_emotion_with_sheets(self, clean_env, fake_comfy):
        make_fake_costumes_dir(
            fake_comfy,
            "Alina",
            costumes={"casual": {"variants": 1, "picked": None}},
            emotions=("happy", "sad"),
        )
        rows = emotion_list.run_list("Alina", comfy_path=str(fake_comfy))
        # Expect: neutral (variants count sheets), happy, sad
        pairs = {(r["costume"], r["emotion"]) for r in rows}
        assert ("casual", "happy") in pairs
        assert ("casual", "sad") in pairs
        # neutral subdir has sheet_neutral_NNNNN_.png too — included.
        assert ("casual", "neutral") in pairs

    def test_skips_emotion_dir_without_sheet_files(self, clean_env, fake_comfy):
        char_dir = fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Alina"
        (char_dir / "Sheets" / "casual" / "empty").mkdir(parents=True)
        rows = emotion_list.run_list("Alina", comfy_path=str(fake_comfy))
        assert rows == []


@pytest.mark.command_graph
class TestEmotionListCli:
    def setup_method(self):
        self.runner = CliRunner()

    def test_exits_zero_with_no_results(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        with patch.object(emotion_list, "run_list", return_value=[]):
            result = self.runner.invoke(root_app, ["emotion","list", "Alina"])
        assert result.exit_code == 0
        assert "No costumes found" in result.stdout

    def test_renders_table(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        fake_rows = [{"costume": "casual", "emotion": "happy", "path": "/tmp/p"}]
        with patch.object(emotion_list, "run_list", return_value=fake_rows):
            result = self.runner.invoke(root_app, ["emotion","list", "Alina"])
        assert result.exit_code == 0
        assert "casual" in result.stdout
        assert "happy" in result.stdout

    def test_json_flag(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        fake_rows = [{"costume": "c", "emotion": "e", "path": "/p"}]
        with patch.object(emotion_list, "run_list", return_value=fake_rows):
            result = self.runner.invoke(root_app, ["emotion","list", "Alina", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.stdout) == fake_rows

    def test_not_found_exits_five(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        err = VnccsNotFoundError("Character not found: 'Nope'")
        with patch.object(emotion_list, "run_list", side_effect=err):
            result = self.runner.invoke(root_app, ["emotion","list", "Nope"])
        assert result.exit_code == 5


# ---------------------------------------------------------------------------
# emotion show — logic
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestEmotionShowLogic:
    def test_unset_comfy_path_raises(self, clean_env):
        with pytest.raises(VnccsPathError) as exc:
            emotion_show.run_show("Alina", emotion="happy")
        assert exc.value.exit_code == 6

    def test_character_not_found_raises(self, clean_env, fake_comfy):
        with pytest.raises(VnccsNotFoundError) as exc:
            emotion_show.run_show("Nobody", emotion="happy", comfy_path=str(fake_comfy))
        assert exc.value.exit_code == 5

    def test_no_sheets_for_emotion_raises(self, clean_env, fake_comfy):
        make_empty_fake_character(fake_comfy, "Alina")
        with pytest.raises(VnccsNotFoundError) as exc:
            emotion_show.run_show("Alina", emotion="happy", comfy_path=str(fake_comfy))
        assert exc.value.exit_code == 5

    def test_unambiguous_auto_costume(self, clean_env, fake_comfy):
        make_fake_costumes_dir(
            fake_comfy,
            "Alina",
            costumes={"casual": {"variants": 1, "picked": None}},
            emotions=("happy",),
        )
        info = emotion_show.run_show(
            "Alina", emotion="happy", comfy_path=str(fake_comfy)
        )
        assert info["costume"] == "casual"
        assert info["emotion"] == "happy"
        assert info["character"] == "Alina"
        assert info["path"].endswith("sheet_happy_00001_.png")
        assert info["size"] > 0
        assert "T" in info["created"] or "-" in info["created"]  # ISO-8601 marker

    def test_ambiguous_costume_raises(self, clean_env, fake_comfy):
        make_fake_costumes_dir(
            fake_comfy,
            "Alina",
            costumes={
                "casual": {"variants": 1, "picked": None},
                "formal": {"variants": 1, "picked": None},
            },
            emotions=("happy",),
        )
        with pytest.raises(VnccsNotFoundError) as exc:
            emotion_show.run_show("Alina", emotion="happy", comfy_path=str(fake_comfy))
        assert exc.value.exit_code == 5
        assert "multiple costumes" in exc.value.message.lower()

    def test_explicit_costume_picked(self, clean_env, fake_comfy):
        make_fake_costumes_dir(
            fake_comfy,
            "Alina",
            costumes={
                "casual": {"variants": 1, "picked": None},
                "formal": {"variants": 1, "picked": None},
            },
            emotions=("happy",),
        )
        info = emotion_show.run_show(
            "Alina",
            emotion="happy",
            costume="formal",
            comfy_path=str(fake_comfy),
        )
        assert info["costume"] == "formal"

    def test_picks_highest_sequence(self, clean_env, fake_comfy):
        make_fake_costumes_dir(
            fake_comfy,
            "Alina",
            costumes={"casual": {"variants": 1, "picked": None}},
            emotions=(),
        )
        emotion_dir = (
            fake_comfy / "output" / "VN_CharacterCreatorSuit"
            / "Alina" / "Sheets" / "casual" / "happy"
        )
        emotion_dir.mkdir(parents=True)
        (emotion_dir / "sheet_happy_00001_.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (emotion_dir / "sheet_happy_00042_.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (emotion_dir / "sheet_happy_00007_.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        info = emotion_show.run_show(
            "Alina",
            emotion="happy",
            costume="casual",
            comfy_path=str(fake_comfy),
        )
        assert info["path"].endswith("sheet_happy_00042_.png")

    def test_hyphenated_emotion_name(self, clean_env, fake_comfy):
        char_dir = fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Alina"
        emotion_dir = char_dir / "Sheets" / "casual" / "radiant-smile"
        emotion_dir.mkdir(parents=True)
        (emotion_dir / "sheet_radiant-smile_00003_.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        info = emotion_show.run_show(
            "Alina",
            emotion="radiant-smile",
            costume="casual",
            comfy_path=str(fake_comfy),
        )
        assert info["emotion"] == "radiant-smile"


@pytest.mark.command_graph
class TestEmotionShowCli:
    def setup_method(self):
        self.runner = CliRunner()

    def test_renders_table(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        info = {
            "character": "Alina",
            "costume": "casual",
            "emotion": "happy",
            "path": "/fake/sheet_happy_00001_.png",
            "size": 512,
            "created": "2026-04-20T12:00:00",
        }
        with patch.object(emotion_show, "run_show", return_value=info):
            result = self.runner.invoke(
                root_app, ["emotion", "show", "Alina", "--emotion", "happy"]
            )
        assert result.exit_code == 0
        assert "Alina" in result.stdout
        assert "happy" in result.stdout
        assert "sheet_happy_00001_.png" in result.stdout

    def test_json_flag(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        info = {
            "character": "A",
            "costume": "c",
            "emotion": "e",
            "path": "/p",
            "size": 1,
            "created": "2026-04-20T00:00:00",
        }
        with patch.object(emotion_show, "run_show", return_value=info):
            result = self.runner.invoke(
                root_app, ["emotion", "show", "A", "--emotion", "e", "--json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.stdout) == info

    def test_costume_flag_forwarded(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        info = {
            "character": "A",
            "costume": "formal",
            "emotion": "e",
            "path": "/p",
            "size": 1,
            "created": "2026-04-20T00:00:00",
        }
        with patch.object(emotion_show, "run_show", return_value=info) as m:
            result = self.runner.invoke(
                root_app,
                ["emotion", "show", "A", "--emotion", "e", "--costume", "formal"],
            )
        assert result.exit_code == 0
        _, call_kwargs = m.call_args
        assert call_kwargs["costume"] == "formal"

    def test_not_found_exits_five(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        err = VnccsNotFoundError("Not found")
        with patch.object(emotion_show, "run_show", side_effect=err):
            result = self.runner.invoke(
                root_app, ["emotion", "show", "Nope", "--emotion", "happy"]
            )
        assert result.exit_code == 5


# ---------------------------------------------------------------------------
# emotion preview — logic
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestEmotionPreviewLogic:
    def test_unset_comfy_path_raises(self, clean_env):
        with pytest.raises(VnccsPathError) as exc:
            emotion_preview.run_preview("Alina", emotion="angry")
        assert exc.value.exit_code == 6

    def test_character_not_found_raises(self, clean_env, fake_comfy):
        with pytest.raises(VnccsNotFoundError) as exc:
            emotion_preview.run_preview("Nobody", emotion="angry", comfy_path=str(fake_comfy))
        assert exc.value.exit_code == 5

    def test_empty_images_dir_raises(self, clean_env, fake_comfy):
        make_empty_fake_character(fake_comfy, "Alina")
        # fake_comfy pre-creates emotions-config/images/ but empty.
        with pytest.raises(VnccsNotFoundError) as exc:
            emotion_preview.run_preview(
                "Alina", emotion="angry", comfy_path=str(fake_comfy)
            )
        assert exc.value.exit_code == 5

    def test_unknown_emotion_raises(self, clean_env, fake_comfy):
        make_empty_fake_character(fake_comfy, "Alina")
        make_fake_emotion_preview(fake_comfy, emotion="angry")
        with pytest.raises(VnccsNotFoundError) as exc:
            emotion_preview.run_preview(
                "Alina", emotion="bogus", comfy_path=str(fake_comfy)
            )
        assert exc.value.exit_code == 5
        assert "bogus" in exc.value.message

    def test_known_emotion_resolves(self, clean_env, fake_comfy):
        make_empty_fake_character(fake_comfy, "Alina")
        preview_path = make_fake_emotion_preview(fake_comfy, emotion="angry")
        info = emotion_preview.run_preview(
            "Alina", emotion="angry", comfy_path=str(fake_comfy)
        )
        assert info["emotion"] == "angry"
        assert info["exists"] is True
        assert Path(info["path"]) == preview_path

    def test_hyphenated_emotion(self, clean_env, fake_comfy):
        make_empty_fake_character(fake_comfy, "Alina")
        make_fake_emotion_preview(fake_comfy, emotion="radiant-smile")
        info = emotion_preview.run_preview(
            "Alina", emotion="radiant-smile", comfy_path=str(fake_comfy)
        )
        assert info["exists"] is True
        assert "radiant-smile" in info["path"]


@pytest.mark.command_graph
class TestEmotionPreviewCli:
    def setup_method(self):
        self.runner = CliRunner()

    def test_prints_path_plain(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        info = {"emotion": "angry", "path": "/x/angry.png", "exists": True}
        with patch.object(emotion_preview, "run_preview", return_value=info):
            result = self.runner.invoke(
                root_app, ["emotion", "preview", "Alina", "--emotion", "angry"]
            )
        assert result.exit_code == 0
        assert "/x/angry.png" in result.stdout

    def test_json_flag_emits_full_dict(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        info = {"emotion": "angry", "path": "/x/angry.png", "exists": True}
        with patch.object(emotion_preview, "run_preview", return_value=info):
            result = self.runner.invoke(
                root_app, ["emotion", "preview", "Alina", "--emotion", "angry", "--json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.stdout) == info

    def test_unknown_emotion_exits_five(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        err = VnccsNotFoundError("Unknown emotion: 'bogus'")
        with patch.object(emotion_preview, "run_preview", side_effect=err):
            result = self.runner.invoke(
                root_app, ["emotion", "preview", "Alina", "--emotion", "bogus"]
            )
        assert result.exit_code == 5

    def test_path_flag_forwarded(self, monkeypatch, tmp_path):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        info = {"emotion": "angry", "path": "/x.png", "exists": True}
        with patch.object(emotion_preview, "run_preview", return_value=info) as m:
            result = self.runner.invoke(
                root_app,
                [
                    "emotion",
                    "preview",
                    "Alina",
                    "--emotion",
                    "angry",
                    "--path",
                    str(tmp_path / "custom"),
                ],
            )
        assert result.exit_code == 0
        _, call_kwargs = m.call_args
        assert call_kwargs["comfy_path"] == str(tmp_path / "custom")
