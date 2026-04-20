"""Tier 1 tests for Wave 3 destructive commands.

Covers:
  - vnccs_cli.commands.character_prune
  - vnccs_cli.commands.clothing_remove
  - vnccs_cli.commands.clothing_pick

All commands operate purely on the filesystem — no ComfyUI contact
needed. Tests build a fake VNCCS state tree in tmp_path via the
existing ``fake_comfy`` + ``make_fake_costumes_dir`` fixtures, then
invoke the logic layer and assert the correct files exist / are gone /
contain the right config JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _vnccs_helpers import make_fake_costumes_dir
from vnccs_cli.backend import (
    VnccsNotFoundError,
    VnccsValidationError,
)
from vnccs_cli.commands import (
    character_prune,
    clothing_pick,
    clothing_remove,
)


# ---------------------------------------------------------------------------
# character prune
# ---------------------------------------------------------------------------


def test_character_prune_removes_entire_tree(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    char_dir = make_fake_costumes_dir(fake_comfy, "Aria")
    # Extra content: sprites + lora
    (char_dir / "Sprites" / "casual" / "happy").mkdir(parents=True)
    (char_dir / "Sprites" / "casual" / "happy" / "s1.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (char_dir / "lora").mkdir()
    (char_dir / "lora" / "c.txt").write_text("caption", encoding="utf-8")

    assert char_dir.is_dir()

    result = character_prune.run_prune("Aria", confirm=True)

    assert not char_dir.exists(), "tree must be gone"
    assert result["character"] == "Aria"
    assert result["removed"]["file_count"] > 0
    assert result["removed"]["total_bytes"] > 0


def test_character_prune_without_confirm_exits_three(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    char_dir = make_fake_costumes_dir(fake_comfy, "Aria")
    with pytest.raises(VnccsValidationError) as ei:
        character_prune.run_prune("Aria", confirm=False)
    assert ei.value.exit_code == 3
    assert char_dir.is_dir(), "tree must NOT be touched without --yes"


def test_character_prune_missing_exits_five(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    with pytest.raises(VnccsNotFoundError) as ei:
        character_prune.run_prune("Ghost", confirm=True)
    assert ei.value.exit_code == 5


def test_character_prune_rejects_dotdot_traversal(fake_comfy, monkeypatch, tmp_path):
    """character=".." must not escape the state tree even if that dir exists."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    state_root = fake_comfy / "output" / "VN_CharacterCreatorSuit"
    state_root.mkdir(parents=True, exist_ok=True)
    # The parent of state_root exists (fake_comfy/output), so `..` would resolve there.
    # run_prune must refuse before touching it.
    with pytest.raises((VnccsValidationError, VnccsNotFoundError)):
        character_prune.run_prune("..", confirm=True)
    # State root still intact
    assert state_root.is_dir()


def test_character_prune_empty_name_raises(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    from vnccs_cli.backend import VnccsError
    with pytest.raises(VnccsError):
        character_prune.run_prune("", confirm=True)


# ---------------------------------------------------------------------------
# clothing remove
# ---------------------------------------------------------------------------


def test_clothing_remove_deletes_costume_and_prunes_config(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    char_dir = make_fake_costumes_dir(fake_comfy, "Aria")
    costume_dir = char_dir / "Sheets" / "casual"
    assert costume_dir.is_dir()

    # Pre-check: config has `casual`
    cfg_path = char_dir / "Aria_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "casual" in cfg["costumes"]

    result = clothing_remove.run_remove("Aria", "casual", confirm=True)

    assert not costume_dir.exists()
    assert result["config_updated"] is True
    # Post: config no longer has `casual`
    cfg_after = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "casual" not in cfg_after["costumes"]
    # Other costumes preserved
    assert "formal" in cfg_after["costumes"]


def test_clothing_remove_without_confirm_exits_three(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    char_dir = make_fake_costumes_dir(fake_comfy, "Aria")
    costume_dir = char_dir / "Sheets" / "casual"
    with pytest.raises(VnccsValidationError) as ei:
        clothing_remove.run_remove("Aria", "casual", confirm=False)
    assert ei.value.exit_code == 3
    assert costume_dir.is_dir()


def test_clothing_remove_refuses_naked_costume(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    char_dir = make_fake_costumes_dir(
        fake_comfy,
        "Aria",
        costumes={"Naked": {"variants": 1}, "casual": {"variants": 1}},
    )
    naked_dir = char_dir / "Sheets" / "Naked"
    assert naked_dir.is_dir()

    with pytest.raises(VnccsValidationError) as ei:
        clothing_remove.run_remove("Aria", "Naked", confirm=True)
    assert ei.value.exit_code == 3
    assert "protected" in ei.value.message.lower() or "Naked" in ei.value.message
    assert naked_dir.is_dir(), "Naked must NOT be touched"


def test_clothing_remove_missing_costume_exits_five(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    make_fake_costumes_dir(fake_comfy, "Aria")
    with pytest.raises(VnccsNotFoundError) as ei:
        clothing_remove.run_remove("Aria", "nonexistent", confirm=True)
    assert ei.value.exit_code == 5


def test_clothing_remove_missing_character_exits_five(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    with pytest.raises(VnccsNotFoundError) as ei:
        clothing_remove.run_remove("Ghost", "any", confirm=True)
    assert ei.value.exit_code == 5


def test_clothing_remove_handles_missing_config_gracefully(fake_comfy, monkeypatch):
    """Dir deletion must succeed even if config file is missing."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    state = fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria"
    costume_dir = state / "Sheets" / "casual" / "neutral"
    costume_dir.mkdir(parents=True)
    (costume_dir / "sheet_neutral_00001_.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    # No config file.

    result = clothing_remove.run_remove("Aria", "casual", confirm=True)
    assert not (state / "Sheets" / "casual").exists()
    assert result["config_updated"] is False


# ---------------------------------------------------------------------------
# clothing pick
# ---------------------------------------------------------------------------


def test_clothing_pick_writes_picked_variant(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    make_fake_costumes_dir(
        fake_comfy,
        "Aria",
        costumes={"casual": {"variants": 3, "picked": None}},
    )

    result = clothing_pick.run_pick("Aria", "casual", 2)

    cfg_path = Path(result["config_path"])
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert cfg["costumes"]["casual"]["picked_variant"] == 2
    assert result["picked_variant"] == 2
    assert result["available_variants"] == [1, 2, 3]


def test_clothing_pick_overwrites_prior_pick(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    make_fake_costumes_dir(
        fake_comfy,
        "Aria",
        costumes={"casual": {"variants": 3, "picked": 1}},
    )

    clothing_pick.run_pick("Aria", "casual", 3)

    cfg_path = (
        fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria"
        / "Aria_config.json"
    )
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert cfg["costumes"]["casual"]["picked_variant"] == 3


def test_clothing_pick_variant_out_of_range_exits_three(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    make_fake_costumes_dir(
        fake_comfy,
        "Aria",
        costumes={"casual": {"variants": 2}},
    )

    with pytest.raises(VnccsValidationError) as ei:
        clothing_pick.run_pick("Aria", "casual", 99)
    assert ei.value.exit_code == 3
    assert "99" in ei.value.message


def test_clothing_pick_negative_variant_exits_three(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    make_fake_costumes_dir(fake_comfy, "Aria", costumes={"casual": {"variants": 1}})
    with pytest.raises(VnccsValidationError):
        clothing_pick.run_pick("Aria", "casual", 0)
    with pytest.raises(VnccsValidationError):
        clothing_pick.run_pick("Aria", "casual", -1)


def test_clothing_pick_missing_character_exits_five(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    with pytest.raises(VnccsNotFoundError) as ei:
        clothing_pick.run_pick("Ghost", "any", 1)
    assert ei.value.exit_code == 5


def test_clothing_pick_missing_costume_exits_five(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    make_fake_costumes_dir(fake_comfy, "Aria", costumes={"casual": {"variants": 1}})
    with pytest.raises(VnccsNotFoundError) as ei:
        clothing_pick.run_pick("Aria", "nonexistent", 1)
    assert ei.value.exit_code == 5


def test_clothing_pick_missing_config_exits_five(fake_comfy, monkeypatch):
    """Variant files exist but no config.json — refuse to fabricate one."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    state = fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria"
    (state / "Sheets" / "casual" / "neutral").mkdir(parents=True)
    (state / "Sheets" / "casual" / "neutral" / "sheet_neutral_00001_.png").write_bytes(
        b"\x89PNG\r\n\x1a\n"
    )
    # No config file.
    with pytest.raises(VnccsNotFoundError) as ei:
        clothing_pick.run_pick("Aria", "casual", 1)
    assert ei.value.exit_code == 5


def test_clothing_pick_preserves_other_costumes(fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    make_fake_costumes_dir(
        fake_comfy,
        "Aria",
        costumes={
            "casual": {"variants": 2, "picked": None},
            "formal": {"variants": 1, "picked": 1},
        },
    )

    clothing_pick.run_pick("Aria", "casual", 2)

    cfg = json.loads(
        (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria" / "Aria_config.json")
        .read_text(encoding="utf-8")
    )
    # casual now picked=2
    assert cfg["costumes"]["casual"]["picked_variant"] == 2
    # formal's existing pick preserved
    assert cfg["costumes"]["formal"]["picked_variant"] == 1
