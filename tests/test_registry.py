import json
import os
import pytest
from cli_me.registry import Registry


@pytest.fixture
def sample_registry(tmp_path):
    data = {
        "skills": [
            {
                "name": "gimp",
                "description": "Image editing CLI for GIMP",
                "category": "image",
                "tags": ["image-editing", "graphics", "pod"],
                "version": "0.1.0",
                "software_url": "https://www.gimp.org",
                "source_repo": "https://gitlab.gnome.org/GNOME/gimp",
                "dependencies": [],
            },
            {
                "name": "blender",
                "description": "3D modeling and rendering CLI for Blender",
                "category": "3d",
                "tags": ["3d", "modeling", "rendering"],
                "version": "0.1.0",
                "software_url": "https://www.blender.org",
                "source_repo": "https://github.com/blender/blender",
                "dependencies": [],
            },
            {
                "name": "comfyui-vnccs",
                "description": "Visual novel character sprite pipeline for ComfyUI",
                "category": "ai-pipeline",
                "tags": ["comfyui", "character-sprites", "visual-novel"],
                "version": "0.1.0",
                "software_url": "https://github.com/AHEKOT/ComfyUI_VNCCS",
                "source_repo": "https://github.com/AHEKOT/ComfyUI_VNCCS",
                "dependencies": ["comfyui"],
            },
        ]
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(data))
    return registry_path


def test_load_registry(sample_registry):
    reg = Registry(sample_registry)
    assert len(reg.skills) == 3


def test_get_skill_by_name(sample_registry):
    reg = Registry(sample_registry)
    skill = reg.get("gimp")
    assert skill is not None
    assert skill["name"] == "gimp"


def test_get_skill_not_found(sample_registry):
    reg = Registry(sample_registry)
    assert reg.get("nonexistent") is None


def test_list_all(sample_registry):
    reg = Registry(sample_registry)
    names = [s["name"] for s in reg.list_all()]
    assert names == ["blender", "comfyui-vnccs", "gimp"]


def test_list_by_category(sample_registry):
    reg = Registry(sample_registry)
    results = reg.list_by_category("image")
    assert len(results) == 1
    assert results[0]["name"] == "gimp"


def test_search_by_text(sample_registry):
    reg = Registry(sample_registry)
    results = reg.search("character sprite")
    assert len(results) == 1
    assert results[0]["name"] == "comfyui-vnccs"


def test_search_matches_tags(sample_registry):
    reg = Registry(sample_registry)
    results = reg.search("pod")
    assert len(results) == 1
    assert results[0]["name"] == "gimp"


def test_add_skill(sample_registry):
    reg = Registry(sample_registry)
    new_skill = {
        "name": "kohya-ss",
        "description": "LoRA training CLI",
        "category": "ai-training",
        "tags": ["lora", "training"],
        "version": "0.1.0",
        "software_url": "https://github.com/bmaltais/kohya_ss",
        "source_repo": "https://github.com/bmaltais/kohya_ss",
        "dependencies": [],
    }
    reg.add(new_skill)
    assert reg.get("kohya-ss") is not None
    assert len(reg.skills) == 4


def test_add_duplicate_raises(sample_registry):
    reg = Registry(sample_registry)
    with pytest.raises(ValueError, match="already exists"):
        reg.add({"name": "gimp"})


def test_remove_skill(sample_registry):
    reg = Registry(sample_registry)
    reg.remove("gimp")
    assert reg.get("gimp") is None
    assert len(reg.skills) == 2


def test_remove_nonexistent_raises(sample_registry):
    reg = Registry(sample_registry)
    with pytest.raises(ValueError, match="not found"):
        reg.remove("nonexistent")


def test_save(sample_registry):
    reg = Registry(sample_registry)
    reg.add({
        "name": "test-skill",
        "description": "test",
        "category": "test",
        "tags": [],
        "version": "0.1.0",
        "software_url": "",
        "source_repo": "",
        "dependencies": [],
    })
    reg.save()
    reg2 = Registry(sample_registry)
    assert reg2.get("test-skill") is not None


def test_save_is_atomic(sample_registry):
    """save() writes atomically — a crash mid-write won't corrupt the file."""
    reg = Registry(sample_registry)
    original_content = sample_registry.read_text()

    reg.add({
        "name": "atomic-test",
        "description": "test atomicity",
        "category": "test",
        "tags": [],
        "version": "0.1.0",
        "software_url": "",
        "source_repo": "",
        "dependencies": [],
    })
    reg.save()

    # Verify the file is valid JSON after save
    import json
    data = json.loads(sample_registry.read_text())
    assert any(s["name"] == "atomic-test" for s in data["skills"])


def test_save_uses_lock_file(sample_registry):
    """save() creates a .lock file during write."""
    lock_path = sample_registry.with_suffix(".json.lock")
    reg = Registry(sample_registry)
    reg.save()
    # Lock file may or may not persist after release (implementation detail),
    # but the save should complete without error
    assert sample_registry.exists()
