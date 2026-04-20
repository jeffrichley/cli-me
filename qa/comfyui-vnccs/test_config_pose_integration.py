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


# Minimal 8-byte PNG magic header (for fixtures that still need it).
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# Minimal valid-ish pose preset JSON. Matches what the stock VNCCS
# vnccs_poseset.json looks like at a top level (a dict with a "poses"
# array). The wrapper only enumerates filenames + size, so contents
# don't need to be parsed — just non-empty and valid JSON.
_POSE_JSON = b'{"poses":[{"name":"placeholder","keypoints":[]}]}'


# ---------------------------------------------------------------------------
# config show — fake_comfy fixture
# ---------------------------------------------------------------------------


class TestConfigShowIntegration:
    def test_run_show_returns_resolved_paths(self, fake_comfy: Path, monkeypatch):
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        monkeypatch.delenv("COMFY_URL", raising=False)
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
        result = config_show.run_show()
        assert Path(result["comfy_path"]) == fake_comfy.resolve()
        assert Path(result["vnccs_install_dir"]) == (
            fake_comfy.resolve() / "custom_nodes" / "ComfyUI_VNCCS"
        )
        assert Path(result["models_root"]) == fake_comfy.resolve() / "models"
        assert Path(result["vnccs_state_dir"]) == (
            fake_comfy.resolve() / "output" / "VN_CharacterCreatorSuit"
        )
        assert result["vnccs_version"] == "2.1.0"
        assert result["comfy_url"] == "http://127.0.0.1:8188"
        assert Path(result["bundled_workflow_dir"]).exists()

    def test_table_shows_expected_fields(self, fake_comfy: Path, monkeypatch):
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        monkeypatch.delenv("COMFY_URL", raising=False)
        monkeypatch.delenv("VNCCS_STATE_DIR", raising=False)
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
            "VNCCS state dir",
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
    """fake_comfy with 3 dummy pose JSON preset files pre-populated.

    VNCCS's poses are JSON pose-data files (BODY_25 skeletons), not
    images — the stock install ships `vnccs_poseset.json` with 12 poses.

    Returns (comfy_root, sorted list of pose filenames).
    """
    poses_dir = fake_comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
    filenames = ["custom_action.json", "stand_set.json", "vnccs_poseset.json"]
    for name in filenames:
        (poses_dir / name).write_bytes(_POSE_JSON)
    return fake_comfy, sorted(filenames)


class TestPoseListIntegration:
    def test_run_list_returns_populated(self, fake_comfy_with_poses, monkeypatch):
        comfy, expected_names = fake_comfy_with_poses
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        result = pose_list.run_list()
        assert [e["name"] for e in result] == expected_names
        for entry in result:
            assert entry["size"] == len(_POSE_JSON)

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
            assert entry["size"] == len(_POSE_JSON)

    def test_non_json_files_ignored(self, fake_comfy: Path, monkeypatch):
        """Images and other non-JSON files in presets/poses/ are not enumerated."""
        poses_dir = fake_comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
        (poses_dir / "preview.png").write_bytes(_PNG_MAGIC)
        (poses_dir / "readme.md").write_text("not a preset")
        (poses_dir / "real.json").write_bytes(_POSE_JSON)
        monkeypatch.setenv("COMFY_PATH", str(fake_comfy))
        result = pose_list.run_list()
        assert [e["name"] for e in result] == ["real.json"]

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
