"""Tier 1 tests for the read-only character commands (`list`, `show`).

These tests exercise the logic functions directly
(`character_list.run_list`, `character_show.run_show`) against temp-file
fixtures that mimic the VNCCS on-disk layout. They are Tier-1 because
they avoid any network call; all filesystem state is inside tmp_path.

State layout reference: references/source-analysis/state-management.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# conftest.py adds skill scripts/ to sys.path
from vnccs_cli import backend
from vnccs_cli.backend import VnccsNotFoundError, VnccsPathError
from vnccs_cli.commands import character_list, character_show


# ---------------------------------------------------------------------------
# Helpers — build a fake VNCCS state dir inside tmp_path.
# ---------------------------------------------------------------------------


def _touch_png(path: Path) -> None:
    """Write 8-byte PNG magic header (enough to satisfy existence checks)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n")


def _make_character_dir(
    root: Path,
    name: str,
    *,
    with_base_sheet: bool = False,
    with_config: bool = False,
    costumes: dict[str, list[str]] | None = None,
    emotions_per_costume: dict[str, list[str]] | None = None,
    sprite_files: int = 0,
    dataset_rows: int = 0,
) -> Path:
    """Materialize a VNCCS character tree under `root`.

    `costumes[name] = [variant_file_names]` drops each variant file into
    `Sheets/{name}/neutral/`. `emotions_per_costume[costume] = [emotions]`
    drops one `sheet_{emotion}_00001_.png` under `Sheets/{costume}/{emotion}/`.
    """
    char = root / name
    char.mkdir(parents=True, exist_ok=True)

    if with_config:
        cfg = {
            "character_info": {"name": name, "sex": "female", "age": 18},
            "folder_structure": {
                "main_directories": ["Sprites", "Faces", "Sheets"],
                "emotions": ["neutral"],
            },
            "config_version": "2.0",
            "costumes": {},
        }
        if costumes:
            for cname in costumes:
                cfg["costumes"][cname] = {}
        (char / f"{name}_config.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    if with_base_sheet:
        _touch_png(char / "Sheets" / "Naked" / "neutral" / "sheet_neutral_00001_.png")

    if costumes:
        for cname, variants in costumes.items():
            for v in variants:
                _touch_png(char / "Sheets" / cname / "neutral" / v)

    if emotions_per_costume:
        for cname, emotions in emotions_per_costume.items():
            for emo in emotions:
                _touch_png(
                    char / "Sheets" / cname / emo / f"sheet_{emo}_00001_.png"
                )

    for i in range(sprite_files):
        _touch_png(
            char / "Sprites" / "Casual" / "neutral" / f"sprite_neutral_{i:05d}_.png"
        )

    if dataset_rows:
        lora = char / "lora"
        lora.mkdir(parents=True, exist_ok=True)
        for i in range(dataset_rows):
            (lora / f"row_{i}.txt").write_text("tags, go, here", encoding="utf-8")
            _touch_png(lora / f"row_{i}.png")

    return char


# ---------------------------------------------------------------------------
# get_vnccs_state_dir — resolution precedence (new backend helper)
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestGetVnccsStateDir:
    def test_explicit_state_dir_wins(self, tmp_path, clean_env):
        explicit = tmp_path / "explicit"
        explicit.mkdir()
        result = backend.get_vnccs_state_dir(state_dir=str(explicit))
        assert result == explicit.resolve()

    def test_env_override_used_when_no_arg(self, tmp_path, clean_env, monkeypatch):
        env_dir = tmp_path / "from_env"
        env_dir.mkdir()
        monkeypatch.setenv("VNCCS_STATE_DIR", str(env_dir))
        result = backend.get_vnccs_state_dir()
        assert result == env_dir.resolve()

    def test_default_under_comfy_path(self, fake_comfy, clean_env, monkeypatch):
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        result = backend.get_vnccs_state_dir()
        assert result == (fake_comfy / "output" / "VN_CharacterCreatorSuit").resolve()

    def test_missing_comfy_path_raises(self, clean_env):
        with pytest.raises(VnccsPathError):
            backend.get_vnccs_state_dir()


# ---------------------------------------------------------------------------
# character list — kitchen-sink
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestCharacterList:
    def test_missing_state_dir_returns_empty(self, tmp_path, clean_env):
        # State dir never created.
        result = character_list.run_list(state_dir=str(tmp_path / "nope"))
        assert result == []

    def test_empty_state_dir_returns_empty(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        result = character_list.run_list(state_dir=str(state))
        assert result == []

    def test_single_character_zero_costumes(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        _make_character_dir(state, "Alina", with_config=True)

        result = character_list.run_list(state_dir=str(state))
        assert len(result) == 1
        r = result[0]
        assert r["name"] == "Alina"
        assert r["costume_count"] == 0
        assert r["emotion_count"] == 0
        assert r["path"].endswith("Alina")
        assert r["last_modified_epoch"] is not None
        # ISO-ish format check (we control the formatter).
        assert " " in r["last_modified"]

    def test_multiple_characters_sorted(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        _make_character_dir(state, "Zoe")
        _make_character_dir(state, "Alina")
        _make_character_dir(state, "Mika")

        result = character_list.run_list(state_dir=str(state))
        names = [r["name"] for r in result]
        assert names == ["Alina", "Mika", "Zoe"]

    def test_character_with_costumes_and_emotions_counts(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        # Alina: 2 costumes ("Naked" + "Casual"), 2 emotion dirs on Casual
        # + 1 on Naked = 3 emotions total (neutral counts as a dir too).
        _make_character_dir(
            state,
            "Alina",
            with_config=True,
            costumes={"Naked": [], "Casual": ["v0.png", "v1.png"]},
            emotions_per_costume={
                "Casual": ["neutral", "happy", "sad"],
                "Naked": ["neutral"],
            },
        )
        result = character_list.run_list(state_dir=str(state))
        assert len(result) == 1
        r = result[0]
        assert r["costume_count"] == 2
        # emotion_count sums across costumes (neutral dirs included).
        assert r["emotion_count"] == 3 + 1

    def test_non_directory_entries_skipped(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        _make_character_dir(state, "Alina")
        # Drop a loose file at the root — must be ignored.
        (state / "not_a_character.txt").write_text("hi", encoding="utf-8")
        result = character_list.run_list(state_dir=str(state))
        assert [r["name"] for r in result] == ["Alina"]

    def test_missing_sheets_dir_is_zero_counts(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        # Bare character directory: no Sheets subdir at all.
        (state / "Sparse").mkdir()
        result = character_list.run_list(state_dir=str(state))
        assert result[0]["costume_count"] == 0
        assert result[0]["emotion_count"] == 0


# ---------------------------------------------------------------------------
# character show — kitchen-sink
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestCharacterShow:
    def test_not_found_raises_exit5(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        with pytest.raises(VnccsNotFoundError) as exc:
            character_show.run_show("Ghost", state_dir=str(state))
        assert exc.value.exit_code == 5
        assert "Ghost" in exc.value.message

    def test_minimal_character(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        _make_character_dir(state, "Alina", with_config=True)

        rec = character_show.run_show("Alina", state_dir=str(state))
        assert rec["name"] == "Alina"
        assert rec["config"]["present"] is True
        assert rec["character_sheet"]["present"] is False
        assert rec["costumes"] == []
        assert rec["emotions"] == []
        assert rec["sprites"]["exists"] is False
        assert rec["sprites"]["png_count"] == 0
        assert rec["dataset"]["exists"] is False

    def test_fully_populated_character(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        _make_character_dir(
            state,
            "Alina",
            with_config=True,
            with_base_sheet=True,
            costumes={
                "Naked": [],
                "Casual": ["v0.png", "v1.png", "v2.png", "v3.png"],
                "Formal": ["v0.png"],
            },
            emotions_per_costume={
                "Casual": ["neutral", "happy", "shy-blush"],
                "Naked": ["neutral"],
            },
            sprite_files=5,
            dataset_rows=3,
        )

        rec = character_show.run_show("Alina", state_dir=str(state))

        # character sheet
        assert rec["character_sheet"]["present"] is True
        assert rec["character_sheet"]["path"].endswith("sheet_neutral_00001_.png")
        assert rec["character_sheet"]["size"] > 0

        # costumes
        names = [c["name"] for c in rec["costumes"]]
        assert set(names) == {"Naked", "Casual", "Formal"}
        by_name = {c["name"]: c for c in rec["costumes"]}
        # 4 v*.png variants + 1 sheet_neutral_00001_.png (from emotions fixture)
        # all land in Sheets/Casual/neutral/; variant_count counts PNGs there.
        assert by_name["Casual"]["variant_count"] == 5
        # 1 v*.png; Formal neutral dir was not targeted by emotions fixture.
        assert by_name["Formal"]["variant_count"] == 1
        # Naked neutral dir picks up the "Naked"/"neutral" fixture sheet.
        assert by_name["Naked"]["variant_count"] == 1
        # picked_variant defaults to None when not written to config.
        assert all(c["picked_variant"] is None for c in rec["costumes"])

        # emotions — "neutral" is intentionally excluded from emotion rows.
        emo_keys = {(e["costume"], e["emotion_type"]) for e in rec["emotions"]}
        assert ("Casual", "happy") in emo_keys
        assert ("Casual", "shy-blush") in emo_keys
        # neutral excluded:
        assert ("Casual", "neutral") not in emo_keys
        assert ("Naked", "neutral") not in emo_keys

        # sprites
        assert rec["sprites"]["exists"] is True
        assert rec["sprites"]["png_count"] == 5

        # dataset
        assert rec["dataset"]["exists"] is True
        assert rec["dataset"]["row_count"] == 3

    def test_picked_variant_round_trips_from_config(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        char = _make_character_dir(
            state, "Alina", with_config=True,
            costumes={"Casual": ["v0.png", "v1.png"]},
        )
        # Overwrite config to inject a picked_variant for "Casual".
        cfg_path = char / "Alina_config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["costumes"]["Casual"] = {"picked_variant": "v1.png"}
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

        rec = character_show.run_show("Alina", state_dir=str(state))
        casual = next(c for c in rec["costumes"] if c["name"] == "Casual")
        assert casual["picked_variant"] == "v1.png"

    def test_config_missing_is_tolerated(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        _make_character_dir(state, "Alina")
        rec = character_show.run_show("Alina", state_dir=str(state))
        assert rec["config"]["present"] is False

    def test_sprites_dir_recursive_count(self, tmp_path, clean_env):
        state = tmp_path / "state"
        state.mkdir()
        char = _make_character_dir(state, "Alina")
        # Drop PNGs under nested subdirs of Sprites/.
        for costume in ("Casual", "Formal"):
            for emo in ("neutral", "happy"):
                for i in range(2):
                    _touch_png(
                        char / "Sprites" / costume / emo / f"sprite_{emo}_{i:05d}_.png"
                    )
        rec = character_show.run_show("Alina", state_dir=str(state))
        assert rec["sprites"]["png_count"] == 2 * 2 * 2
