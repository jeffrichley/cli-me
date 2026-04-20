"""Tier 2 integration tests for `vnccs config show` and `vnccs pose list`.

Filesystem-only. Uses the `fake_comfy` fixture from conftest to build a
realistic ComfyUI + VNCCS tree in tmp_path. No HTTP, no real ComfyUI,
no GPU — the GPU is reserved for the user's training run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

# conftest.py adds skill scripts/ to sys.path
from vnccs_cli import app as root_app
from vnccs_cli.commands import config_show, pose_list


pytestmark = pytest.mark.integration


# Minimal 8-byte PNG magic header. Enough that `pose list`'s size read
# returns a non-zero positive number, without pulling Pillow into test deps.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# config show — fake_comfy fixture
# ---------------------------------------------------------------------------


class TestConfigShowIntegration:
    def test_run_show_returns_resolved_paths(self, fake_comfy: Path, monkeypatch):
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        monkeypatch.delenv("COMFY_URL", raising=False)
        result = config_show.run_show()
        assert Path(result["comfy_path"]) == fake_comfy.resolve()
        assert Path(result["vnccs_install_dir"]) == (
            fake_comfy.resolve() / "custom_nodes" / "ComfyUI_VNCCS"
        )
        assert Path(result["models_root"]) == fake_comfy.resolve() / "models"
        assert Path(result["output_dir"]) == fake_comfy.resolve() / "output"
        assert result["vnccs_version"] == "2.1.0"
        assert result["comfy_url"] == "http://127.0.0.1:8188"
        assert Path(result["bundled_workflow_dir"]).exists()

    def test_table_shows_expected_fields(self, fake_comfy: Path, monkeypatch):
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        monkeypatch.delenv("COMFY_URL", raising=False)
        runner = CliRunner()
        result = runner.invoke(root_app, ["config", "show"])
        assert result.exit_code == 0
        for expected in [
            "COMFY_PATH",
            "COMFY_URL",
            "VNCCS install dir",
            "VNCCS version",
            "Bundled workflow dir",
            "Models root",
            "Output dir",
            "2.1.0",
            "127.0.0.1:8188",
        ]:
            assert expected in result.stdout, f"missing: {expected!r}"

    def test_json_output_is_parseable_and_complete(self, fake_comfy: Path, monkeypatch):
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        monkeypatch.delenv("COMFY_URL", raising=False)
        runner = CliRunner()
        result = runner.invoke(root_app, ["config", "show", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["vnccs_version"] == "2.1.0"
        assert Path(data["comfy_path"]) == fake_comfy.resolve()
        assert Path(data["vnccs_install_dir"]).exists()


# ---------------------------------------------------------------------------
# pose list — fake_comfy fixture with pre-populated presets
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_comfy_with_poses(fake_comfy: Path) -> tuple[Path, list[str]]:
    """fake_comfy with 3 dummy pose PNGs pre-populated.

    Returns (comfy_root, sorted list of pose filenames).
    """
    poses_dir = fake_comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
    filenames = ["action_jump.png", "stand_idle.png", "wave_hello.png"]
    for name in filenames:
        (poses_dir / name).write_bytes(_PNG_MAGIC)
    return fake_comfy, sorted(filenames)


class TestPoseListIntegration:
    def test_run_list_returns_populated(self, fake_comfy_with_poses, monkeypatch):
        comfy, expected_names = fake_comfy_with_poses
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        result = pose_list.run_list()
        assert [e["name"] for e in result] == expected_names
        for entry in result:
            assert entry["size"] == len(_PNG_MAGIC)

    def test_table_contains_filenames(self, fake_comfy_with_poses, monkeypatch):
        comfy, expected_names = fake_comfy_with_poses
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list"])
        assert result.exit_code == 0
        for name in expected_names:
            assert name in result.stdout

    def test_json_array_structure(self, fake_comfy_with_poses, monkeypatch):
        comfy, expected_names = fake_comfy_with_poses
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert [e["name"] for e in data] == expected_names
        for entry in data:
            assert set(entry.keys()) == {"name", "size"}
            assert entry["size"] == len(_PNG_MAGIC)

    def test_empty_poses_dir_prints_not_found(self, fake_comfy: Path, monkeypatch):
        # fake_comfy ships with the presets/poses/ dir already created but empty.
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list"])
        assert result.exit_code == 0
        assert "No poses found" in result.stdout

    def test_no_vnccs_returns_exit_6(self, fake_comfy_no_vnccs: Path, monkeypatch):
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy_no_vnccs))
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list"])
        assert result.exit_code == 6
