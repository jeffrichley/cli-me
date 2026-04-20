"""Tier 1 (mocked) tests for `vnccs config show` and `vnccs pose list`.

Exercises the logic layer directly — no subprocess invocation, no real
ComfyUI install needed. `Path.exists` / `Path.iterdir` and env vars are
mocked to hit every branch.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# conftest.py adds skill scripts/ to sys.path
from vnccs_cli import app as root_app
from vnccs_cli import backend
from vnccs_cli.backend import DEFAULT_COMFY_URL, VnccsPathError
from vnccs_cli.commands import config_show, pose_list


# ---------------------------------------------------------------------------
# config show — logic layer
# ---------------------------------------------------------------------------


def _make_fake_comfy(root: Path, *, with_vnccs: bool = True, version: str | None = "2.1.0") -> Path:
    """Build a minimal fake ComfyUI install at `root` for tests.

    `with_vnccs=True` writes a ComfyUI_VNCCS subdir; `version` controls
    the pyproject.toml content (None = no pyproject, "" = empty file).
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "custom_nodes").mkdir(exist_ok=True)
    (root / "models").mkdir(exist_ok=True)
    (root / "output").mkdir(exist_ok=True)
    (root / "main.py").write_text("# fake\n", encoding="utf-8")
    if with_vnccs:
        vnccs = root / "custom_nodes" / "ComfyUI_VNCCS"
        vnccs.mkdir(exist_ok=True)
        (vnccs / "presets" / "poses").mkdir(parents=True, exist_ok=True)
        if version is not None:
            pyproject = f'[project]\nname = "vnccs"\nversion = "{version}"\n' if version else ""
            (vnccs / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


@pytest.mark.command_graph
class TestConfigShowLogic:
    def test_unset_comfy_path_raises_path_error(self, clean_env):
        with pytest.raises(VnccsPathError) as exc:
            config_show.run_show()
        assert exc.value.exit_code == 6

    def test_returns_all_expected_keys(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        result = config_show.run_show(comfy_path=str(comfy))
        assert set(result.keys()) == {
            "comfy_path",
            "comfy_url",
            "vnccs_install_dir",
            "vnccs_version",
            "bundled_workflow_dir",
            "models_root",
            "vnccs_state_dir",
        }

    def test_paths_are_derived_from_comfy(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        result = config_show.run_show(comfy_path=str(comfy))
        assert Path(result["comfy_path"]) == comfy.resolve()
        assert Path(result["vnccs_install_dir"]) == (
            comfy.resolve() / "custom_nodes" / "ComfyUI_VNCCS"
        )
        assert Path(result["models_root"]) == comfy.resolve() / "models"
        # vnccs_state_dir defaults to <comfy>/output/VN_CharacterCreatorSuit
        # (same helper every other command uses — verifies consistency).
        assert Path(result["vnccs_state_dir"]) == (
            comfy.resolve() / "output" / "VN_CharacterCreatorSuit"
        )

    def test_state_dir_honors_env(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        custom = tmp_path / "custom_state"
        custom.mkdir()
        monkeypatch.setenv("VNCCS_STATE_DIR", str(custom))
        result = config_show.run_show(comfy_path=str(comfy))
        assert Path(result["vnccs_state_dir"]) == custom.resolve()

    def test_url_default_when_env_unset(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        result = config_show.run_show(comfy_path=str(comfy))
        assert result["comfy_url"] == DEFAULT_COMFY_URL

    def test_url_env_var_honored(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        monkeypatch.setenv("COMFY_URL", "http://example.test:9000/")
        result = config_show.run_show(comfy_path=str(comfy))
        # trailing slash stripped per backend.get_comfy_url convention
        assert result["comfy_url"] == "http://example.test:9000"

    def test_url_flag_overrides_env(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        monkeypatch.setenv("COMFY_URL", "http://from-env:1/")
        result = config_show.run_show(comfy_path=str(comfy), url="http://from-flag:2/")
        assert result["comfy_url"] == "http://from-flag:2"

    def test_version_parsed_from_pyproject(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI", version="2.1.0")
        result = config_show.run_show(comfy_path=str(comfy))
        assert result["vnccs_version"] == "2.1.0"

    def test_version_unknown_when_no_pyproject(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI", version=None)
        result = config_show.run_show(comfy_path=str(comfy))
        assert result["vnccs_version"] == "unknown"

    def test_version_unknown_when_pyproject_empty(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI", version="")
        result = config_show.run_show(comfy_path=str(comfy))
        assert result["vnccs_version"] == "unknown"

    def test_version_ignores_poetry_dependency_version(self, clean_env, tmp_path):
        """Version parser must pick [project].version, not a dependency block's
        version.

        A ``[tool.poetry.dependencies.sibling]`` block with its own ``version``
        line appearing BEFORE ``[project]`` would false-match the old
        line-anchored regex and report the dependency's version as VNCCS's
        (r4/config+pose latent-bug finding C2). Pin the tomllib-correct
        behavior.
        """
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        pyproject = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "pyproject.toml"
        pyproject.write_text(
            "[tool.poetry.dependencies.sibling]\n"
            'version = "9.9.9"\n'
            "\n"
            "[project]\n"
            'name = "vnccs"\n'
            'version = "2.1.0"\n',
            encoding="utf-8",
        )
        result = config_show.run_show(comfy_path=str(comfy))
        assert result["vnccs_version"] == "2.1.0"

    def test_version_parses_single_quoted_toml(self, clean_env, tmp_path):
        """TOML allows single-quoted strings; tomllib handles them correctly
        where the old double-quote-only regex did not."""
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        pyproject = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "pyproject.toml"
        pyproject.write_text(
            "[project]\n"
            "name = 'vnccs'\n"
            "version = '2.2.3'\n",
            encoding="utf-8",
        )
        result = config_show.run_show(comfy_path=str(comfy))
        assert result["vnccs_version"] == "2.2.3"

    def test_version_unknown_when_vnccs_not_installed(self, clean_env, tmp_path):
        # config show should not fail if VNCCS isn't installed — it just
        # reports the expected install dir and "unknown" version.
        comfy = _make_fake_comfy(tmp_path / "ComfyUI", with_vnccs=False)
        result = config_show.run_show(comfy_path=str(comfy))
        assert result["vnccs_version"] == "unknown"
        assert Path(result["vnccs_install_dir"]) == (
            comfy.resolve() / "custom_nodes" / "ComfyUI_VNCCS"
        )

    def test_bundled_workflow_dir_absolute_and_points_to_scripts_workflows(
        self, clean_env, tmp_path
    ):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        result = config_show.run_show(comfy_path=str(comfy))
        wf_dir = Path(result["bundled_workflow_dir"])
        assert wf_dir.is_absolute()
        assert wf_dir.name == "workflows"
        # Independent of `comfy`: always inside this skill's scripts/.
        assert str(wf_dir).replace("\\", "/").endswith(
            "skill-repo/comfyui-vnccs/scripts/workflows"
        )


# ---------------------------------------------------------------------------
# config show — Typer dispatch (via CliRunner)
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestConfigShowDispatch:
    def test_table_output_default(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["config", "show"])
        assert result.exit_code == 0
        # Table labels present
        assert "COMFY_PATH" in result.stdout
        assert "VNCCS version" in result.stdout
        assert "2.1.0" in result.stdout

    def test_json_output_is_valid_and_has_all_fields(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["config", "show", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert set(data.keys()) == {
            "comfy_path",
            "comfy_url",
            "vnccs_install_dir",
            "vnccs_version",
            "bundled_workflow_dir",
            "models_root",
            "vnccs_state_dir",
        }
        assert data["vnccs_version"] == "2.1.0"

    def test_exit_6_when_path_unresolvable(self, clean_env):
        runner = CliRunner()
        result = runner.invoke(root_app, ["config", "show"])
        assert result.exit_code == 6

    def test_flag_override_path(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        runner = CliRunner()
        result = runner.invoke(root_app, ["config", "show", "--path", str(comfy), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert Path(data["comfy_path"]) == comfy.resolve()

    def test_flag_override_url(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        runner = CliRunner()
        result = runner.invoke(
            root_app,
            ["config", "show", "--path", str(comfy), "--url", "http://custom:7777", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["comfy_url"] == "http://custom:7777"


# ---------------------------------------------------------------------------
# pose list — logic layer
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestPoseListLogic:
    def test_unset_comfy_path_raises(self, clean_env):
        with pytest.raises(VnccsPathError) as exc:
            pose_list.run_list()
        assert exc.value.exit_code == 6

    def test_missing_vnccs_raises(self, clean_env, tmp_path):
        # ComfyUI exists but VNCCS doesn't — get_vnccs_install_dir raises.
        comfy = _make_fake_comfy(tmp_path / "ComfyUI", with_vnccs=False)
        with pytest.raises(VnccsPathError) as exc:
            pose_list.run_list(comfy_path=str(comfy))
        assert exc.value.exit_code == 6

    def test_empty_dir_returns_empty_list(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        result = pose_list.run_list(comfy_path=str(comfy))
        assert result == []

    def test_missing_poses_subdir_returns_empty(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        # Remove the poses subdir the fixture pre-creates
        poses = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
        poses.rmdir()
        result = pose_list.run_list(comfy_path=str(comfy))
        assert result == []

    def test_enumerates_supported_extensions(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        poses_dir = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
        (poses_dir / "vnccs_poseset.json").write_bytes(b'{"poses":[]}')
        (poses_dir / "custom_a.json").write_bytes(b'{"poses":[]}')
        # Non-JSON files should be filtered (images, docs, etc.)
        (poses_dir / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (poses_dir / "readme.txt").write_text("ignore me\n")
        result = pose_list.run_list(comfy_path=str(comfy))
        names = [e["name"] for e in result]
        assert names == ["custom_a.json", "vnccs_poseset.json"]
        for entry in result:
            assert entry["size"] > 0

    def test_sort_by_filename(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        poses_dir = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
        for name in ["zeta.json", "alpha.json", "mid.json"]:
            (poses_dir / name).write_bytes(b'{"poses":[]}')
        result = pose_list.run_list(comfy_path=str(comfy))
        assert [e["name"] for e in result] == ["alpha.json", "mid.json", "zeta.json"]

    def test_case_insensitive_extension(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        poses_dir = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
        (poses_dir / "upper.JSON").write_bytes(b'{"poses":[]}')
        (poses_dir / "mixed.Json").write_bytes(b'{"poses":[]}')
        result = pose_list.run_list(comfy_path=str(comfy))
        names = {e["name"] for e in result}
        assert names == {"upper.JSON", "mixed.Json"}

    def test_subdirectories_ignored(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        poses_dir = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
        (poses_dir / "nested").mkdir()
        (poses_dir / "nested" / "deep.json").write_bytes(b'{"poses":[]}')
        (poses_dir / "real.json").write_bytes(b'{"poses":[]}')
        result = pose_list.run_list(comfy_path=str(comfy))
        assert [e["name"] for e in result] == ["real.json"]

    def test_iterdir_mocked(self, clean_env, tmp_path):
        """Verify logic walks iterdir() results — directly mock it."""
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        poses_dir = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"

        fake_json = MagicMock(spec=Path)
        fake_json.name = "mocked.json"
        fake_json.suffix = ".json"
        fake_json.is_file.return_value = True
        fake_stat = MagicMock()
        fake_stat.st_size = 42
        fake_json.stat.return_value = fake_stat

        with patch.object(Path, "iterdir", return_value=[fake_json]):
            # keep is_dir working for the outer directory check
            with patch.object(Path, "is_dir", return_value=True):
                result = pose_list.run_list(comfy_path=str(comfy))
        assert result == [{"name": "mocked.json", "size": 42}]


# ---------------------------------------------------------------------------
# pose list — Typer dispatch
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestPoseListDispatch:
    def test_empty_prints_no_poses_found(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list"])
        assert result.exit_code == 0
        assert "No poses found" in result.stdout

    def test_table_includes_filenames(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        poses_dir = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
        (poses_dir / "vnccs_poseset.json").write_bytes(b'{"poses":[]}' * 100)
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list"])
        assert result.exit_code == 0
        assert "vnccs_poseset.json" in result.stdout

    def test_json_output_is_valid_array(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        poses_dir = comfy / "custom_nodes" / "ComfyUI_VNCCS" / "presets" / "poses"
        (poses_dir / "a.json").write_bytes(b'{"poses":[]}')
        (poses_dir / "b.json").write_bytes(b'{"poses":[]}')
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 2
        for entry in data:
            assert set(entry.keys()) == {"name", "size"}
            assert isinstance(entry["size"], int)

    def test_json_empty_is_empty_array(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.stdout) == []

    def test_exit_6_when_vnccs_missing(self, clean_env, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI", with_vnccs=False)
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list"])
        assert result.exit_code == 6

    def test_flag_override_path(self, clean_env, tmp_path):
        comfy = _make_fake_comfy(tmp_path / "ComfyUI")
        runner = CliRunner()
        result = runner.invoke(root_app, ["pose", "list", "--path", str(comfy), "--json"])
        assert result.exit_code == 0
        assert json.loads(result.stdout) == []
