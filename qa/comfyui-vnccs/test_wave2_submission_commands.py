"""Tier 1 tests for Wave 2 submission commands.

Covers the logic layer in:
  - vnccs_cli.commands.character_create
  - vnccs_cli.commands.character_clone
  - vnccs_cli.commands.clothing_add
  - vnccs_cli.commands.emotion_add
  - vnccs_cli.commands.sprite_render
  - vnccs_cli.commands.dataset_export

All tests monkeypatch ``backend.submit_workflow`` and
``backend.wait_for_prompt`` so no real ComfyUI contact occurs. The
character-state fixtures (``fake_comfy``) already exist in conftest.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vnccs_cli import backend
from vnccs_cli.backend import (
    VnccsExecutionError,
    VnccsNotFoundError,
    VnccsValidationError,
)
from vnccs_cli.commands import (
    character_clone,
    character_create,
    clothing_add,
    dataset_export,
    emotion_add,
    sprite_render,
)


# ---------------------------------------------------------------------------
# Shared mock infra — capture workflow + url on submit, short-circuit wait.
# ---------------------------------------------------------------------------


class SubmitRecorder:
    """Drop-in for ``backend.submit_workflow`` — records calls, returns stub."""

    def __init__(self, prompt_id: str = "stub-prompt", node_errors=None):
        self.prompt_id = prompt_id
        self.node_errors = node_errors or {}
        self.calls: list[dict] = []

    def __call__(self, workflow, *, url=None, client_id=None, timeout=30.0):
        # Deep-ish copy so later mutations to the workflow dict in the
        # command don't retroactively mutate our recorded version.
        self.calls.append(
            {
                "workflow": json.loads(json.dumps(workflow)),
                "url": url,
                "client_id": client_id,
            }
        )
        return {
            "prompt_id": self.prompt_id,
            "client_id": client_id or "stub-client",
            "number": 1,
            "node_errors": self.node_errors,
        }


class WaitRecorder:
    """Drop-in for ``backend.wait_for_prompt`` — records + returns stub entry."""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, prompt_id, *, url=None, timeout=600.0):
        self.calls.append({"prompt_id": prompt_id, "url": url, "timeout": timeout})
        return {
            "status": {"status_str": "success", "messages": []},
            "outputs": {"5": {"images": [{"filename": "stub.png"}]}},
        }


@pytest.fixture
def submit_recorder(monkeypatch):
    rec = SubmitRecorder()
    monkeypatch.setattr(backend, "submit_workflow", rec)
    # The command modules import submit_workflow by name — also patch those.
    for mod in (character_create, character_clone, clothing_add,
                emotion_add, sprite_render, dataset_export):
        monkeypatch.setattr(mod, "submit_workflow", rec)
    return rec


@pytest.fixture
def wait_recorder(monkeypatch):
    rec = WaitRecorder()
    monkeypatch.setattr(backend, "wait_for_prompt", rec)
    for mod in (character_create, character_clone, clothing_add,
                emotion_add, sprite_render, dataset_export):
        monkeypatch.setattr(mod, "wait_for_prompt", rec)
    return rec


def _find_node_inputs(workflow: dict, class_type: str, title: str | None = None) -> dict:
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") != class_type:
            continue
        if title is not None:
            meta = node.get("_meta") or {}
            if meta.get("title") != title:
                continue
        return node["inputs"]
    raise AssertionError(
        f"No node with class_type={class_type!r} title={title!r} in recorded workflow"
    )


# ---------------------------------------------------------------------------
# character create
# ---------------------------------------------------------------------------


def test_character_create_patches_creator_and_submits(submit_recorder, wait_recorder):
    result = character_create.run_create(
        "Aria", "tall elf, silver hair, green eyes", seed=12345
    )
    assert len(submit_recorder.calls) == 1
    inputs = _find_node_inputs(submit_recorder.calls[0]["workflow"], "CharacterCreator")
    assert inputs["new_character_name"] == "Aria"
    assert inputs["existing_character"] == "Aria"
    assert inputs["additional_details"] == "tall elf, silver hair, green eyes"
    assert inputs["seed"] == 12345

    # Default wait=True: wait_for_prompt called once
    assert len(wait_recorder.calls) == 1
    assert wait_recorder.calls[0]["prompt_id"] == "stub-prompt"

    assert result["prompt_id"] == "stub-prompt"
    assert result["history"]["status"]["status_str"] == "success"


def test_character_create_without_seed_leaves_workflow_default(submit_recorder, wait_recorder):
    character_create.run_create("Bob", "rogue")
    inputs = _find_node_inputs(submit_recorder.calls[0]["workflow"], "CharacterCreator")
    # Workflow default seed is 1125899906842624 (from the bundled JSON);
    # absence of --seed should leave it untouched.
    assert inputs["seed"] == 1125899906842624


def test_character_create_pose_patches_load_image_node(submit_recorder, wait_recorder):
    character_create.run_create("Zara", "mage", pose="short_body6")
    loader = _find_node_inputs(
        submit_recorder.calls[0]["workflow"],
        "LoadImage",
        title="Character sheet",
    )
    assert loader["image"] == "short_body6.png"


def test_character_create_wait_false_skips_polling(submit_recorder, wait_recorder):
    result = character_create.run_create("Dee", "warrior", wait=False)
    assert submit_recorder.calls, "should have submitted"
    assert wait_recorder.calls == [], "wait=False must not poll"
    assert "history" not in result


# ---------------------------------------------------------------------------
# character clone
# ---------------------------------------------------------------------------


def test_character_clone_patches_both_names(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    # Pre-populate the source character dir
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Parent").mkdir(parents=True)

    result = character_clone.run_clone(
        "Child", "Parent", prompt="younger version", seed=42
    )
    assert len(submit_recorder.calls) == 1
    inputs = _find_node_inputs(submit_recorder.calls[0]["workflow"], "CharacterCreator")
    assert inputs["new_character_name"] == "Child"
    assert inputs["existing_character"] == "Parent"
    assert inputs["additional_details"] == "younger version"
    assert inputs["seed"] == 42
    assert result["history"]["status"]["status_str"] == "success"


def test_character_clone_missing_source_exits_five(submit_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    with pytest.raises(VnccsNotFoundError) as ei:
        character_clone.run_clone("Child", "DoesNotExist")
    assert ei.value.exit_code == 5
    assert submit_recorder.calls == [], "must not submit when source missing"


def test_character_clone_does_not_require_prompt(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Source").mkdir(parents=True)
    character_clone.run_clone("Derived", "Source")
    inputs = _find_node_inputs(submit_recorder.calls[0]["workflow"], "CharacterCreator")
    assert inputs["new_character_name"] == "Derived"
    assert inputs["existing_character"] == "Source"


# ---------------------------------------------------------------------------
# clothing add
# ---------------------------------------------------------------------------


def test_clothing_add_single_variant(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)

    result = clothing_add.run_add(
        "Aria", "school", "white sailor fuku", variants=1, seed=100
    )
    assert len(submit_recorder.calls) == 1
    inputs = _find_node_inputs(
        submit_recorder.calls[0]["workflow"], "CharacterAssetSelector"
    )
    assert inputs["character"] == "Aria"
    assert inputs["new_costume_name"] == "school"
    assert inputs["top"] == "white sailor fuku"
    assert result["variants"] == 1
    assert len(result["submissions"]) == 1
    assert result["submissions"][0]["variant_index"] == 0
    assert result["submissions"][0]["variant_seed"] == 100


def test_clothing_add_multiple_variants_distinct_seeds(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)

    result = clothing_add.run_add(
        "Aria", "beach", "bikini", variants=3, seed=50
    )
    assert len(submit_recorder.calls) == 3
    seeds = [s["variant_seed"] for s in result["submissions"]]
    assert seeds == [50, 51, 52], "deterministic +1 sequence from base seed"
    assert len({s["prompt_id"] for s in result["submissions"]}) == 1  # mock returns same


def test_clothing_add_random_seeds_when_none_given(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)

    result = clothing_add.run_add("Aria", "casual", "jeans", variants=2, seed=None)
    seeds = [s["variant_seed"] for s in result["submissions"]]
    assert len(set(seeds)) == 2, "random seeds must differ"
    for s in seeds:
        assert 0 <= s < 2**31 - 1


def test_clothing_add_missing_character_exits_five(submit_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    with pytest.raises(VnccsNotFoundError) as ei:
        clothing_add.run_add("Ghost", "any", "anything")
    assert ei.value.exit_code == 5
    assert submit_recorder.calls == []


def test_clothing_add_zero_variants_rejected(submit_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)
    with pytest.raises(VnccsValidationError):
        clothing_add.run_add("Aria", "c", "d", variants=0)
    with pytest.raises(VnccsValidationError):
        clothing_add.run_add("Aria", "c", "d", variants=-1)


# ---------------------------------------------------------------------------
# emotion add
# ---------------------------------------------------------------------------


def test_emotion_add_legacy_is_default(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)

    emotion_add.run_add("Aria", "happy")
    inputs = _find_node_inputs(
        submit_recorder.calls[0]["workflow"], "EmotionGeneratorV2"
    )
    assert inputs["character"] == "Aria"
    assert inputs["emotions_data"] == json.dumps(["happy"])
    assert inputs["costumes_data"] == json.dumps(["Naked"])  # default costume
    assert inputs["prompt_style"] == "SDXL Style"


def test_emotion_add_custom_costume(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)

    emotion_add.run_add("Aria", "sad", costume="school")
    inputs = _find_node_inputs(
        submit_recorder.calls[0]["workflow"], "EmotionGeneratorV2"
    )
    assert inputs["costumes_data"] == json.dumps(["school"])


def test_emotion_add_qwen_refuses_exit_four(submit_recorder, fake_comfy, monkeypatch):
    """--qwen path must refuse BEFORE submission due to upstream bug."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)

    with pytest.raises(VnccsExecutionError) as ei:
        emotion_add.run_add("Aria", "happy", legacy=False, qwen=True)
    assert ei.value.exit_code == 4
    assert "VNCCS_QWEN_Detailer" in (ei.value.detail or "")
    assert submit_recorder.calls == [], "must not submit broken QWEN workflow"


def test_emotion_add_both_flags_rejected(submit_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)
    with pytest.raises(VnccsValidationError):
        emotion_add.run_add("Aria", "happy", legacy=True, qwen=True)
    assert submit_recorder.calls == []


def test_emotion_add_missing_character(submit_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    with pytest.raises(VnccsNotFoundError) as ei:
        emotion_add.run_add("Ghost", "happy")
    assert ei.value.exit_code == 5


# ---------------------------------------------------------------------------
# sprite render
# ---------------------------------------------------------------------------


def test_sprite_render_patches_character(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)

    sprite_render.run_render("Aria")
    inputs = _find_node_inputs(
        submit_recorder.calls[0]["workflow"], "SpriteGenerator"
    )
    assert inputs["character"] == "Aria"


def test_sprite_render_missing_character(submit_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    with pytest.raises(VnccsNotFoundError):
        sprite_render.run_render("Ghost")
    assert submit_recorder.calls == []


def test_sprite_render_wait_false_skips_polling(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)
    sprite_render.run_render("Aria", wait=False)
    assert wait_recorder.calls == []


# ---------------------------------------------------------------------------
# dataset export
# ---------------------------------------------------------------------------


def test_dataset_export_patches_character_and_game(submit_recorder, wait_recorder, fake_comfy, monkeypatch, tmp_path):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)

    out_dir = tmp_path / "export"
    # Pre-populate a fake lora/ tree that the copy step will pick up.
    lora_src = fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria" / "lora"
    lora_src.mkdir(parents=True)
    (lora_src / "001.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (lora_src / "001.txt").write_text("caption one", encoding="utf-8")

    result = dataset_export.run_export(
        "Aria", out=str(out_dir), game_name="MyGame"
    )
    inputs = _find_node_inputs(
        submit_recorder.calls[0]["workflow"], "DatasetGenerator"
    )
    assert inputs["character"] == "Aria"
    assert inputs["game_name"] == "MyGame"

    # Copy step
    assert result["out"] == str(out_dir.resolve())
    assert result["copy_stats"]["png_count"] == 1
    assert result["copy_stats"]["txt_count"] == 1
    assert (out_dir / "001.png").exists()
    assert (out_dir / "001.txt").read_text(encoding="utf-8") == "caption one"


def test_dataset_export_without_out_skips_copy(submit_recorder, wait_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)

    result = dataset_export.run_export("Aria")
    assert "out" not in result
    assert "copy_stats" not in result
    assert result["game_name"] == "VN"  # default
    assert result["vnccs_lora_dir"].endswith("lora")


def test_dataset_export_without_wait_skips_copy(submit_recorder, wait_recorder, fake_comfy, monkeypatch, tmp_path):
    """--wait=False means we haven't confirmed completion, so don't copy yet."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)
    lora_src = fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria" / "lora"
    lora_src.mkdir(parents=True)
    (lora_src / "001.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    result = dataset_export.run_export(
        "Aria", out=str(tmp_path / "nope"), wait=False
    )
    assert "out" not in result
    assert wait_recorder.calls == []


def test_dataset_export_missing_character(submit_recorder, fake_comfy, monkeypatch):
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    with pytest.raises(VnccsNotFoundError):
        dataset_export.run_export("Ghost")
    assert submit_recorder.calls == []


def test_dataset_export_missing_lora_dir_after_completion(submit_recorder, wait_recorder, fake_comfy, monkeypatch, tmp_path):
    """VNCCS succeeded but did not write lora/ — surface as exit 5."""
    monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
    (fake_comfy / "output" / "VN_CharacterCreatorSuit" / "Aria").mkdir(parents=True)
    # Note: NO lora/ dir created.

    with pytest.raises(VnccsNotFoundError) as ei:
        dataset_export.run_export("Aria", out=str(tmp_path / "out"))
    assert ei.value.exit_code == 5
    assert "lora/" in ei.value.message
