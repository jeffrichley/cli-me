"""Tier 1 (mocked) tests for the custom-nodes command group."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# conftest.py adds skill scripts/ to sys.path
from comfyui_cli import backend
from comfyui_cli.backend import (
    ComfyError,
    ComfyPathError,
    ComfySubprocessError,
)
from comfyui_cli.commands import (
    custom_nodes_install,
    custom_nodes_list,
    custom_nodes_remove,
    custom_nodes_update,
)


# ---------------------------------------------------------------------------
# get_comfy_path
# ---------------------------------------------------------------------------


def _make_fake_comfy(root: Path) -> Path:
    """Build a minimal fake ComfyUI install root in `root` and return it."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "custom_nodes").mkdir(exist_ok=True)
    (root / "main.py").write_text("# fake comfy entry point\n", encoding="utf-8")
    return root


@pytest.mark.command_graph
class TestGetComfyPath:
    def test_unset_raises_with_helpful_message(self, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        with pytest.raises(ComfyPathError) as exc:
            backend.get_comfy_path(None)
        assert "not set" in exc.value.message.lower()
        assert "COMFY_PATH" in (exc.value.detail or "")

    def test_missing_path_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        bogus = tmp_path / "does_not_exist"
        with pytest.raises(ComfyPathError) as exc:
            backend.get_comfy_path(str(bogus))
        assert "does not exist" in exc.value.message.lower()

    def test_path_without_custom_nodes_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        (tmp_path / "main.py").write_text("# fake\n")
        with pytest.raises(ComfyPathError) as exc:
            backend.get_comfy_path(str(tmp_path))
        assert "not a comfyui install" in exc.value.message.lower()

    def test_valid_path_returns_resolved(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        result = backend.get_comfy_path(str(comfy))
        assert result == comfy.resolve()

    def test_env_var_used_when_no_flag(self, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "comfy")
        monkeypatch.setenv("COMFY_PATH", str(comfy))
        result = backend.get_comfy_path(None)
        assert result == comfy.resolve()

    def test_flag_overrides_env(self, tmp_path, monkeypatch):
        comfy_a = _make_fake_comfy(tmp_path / "a")
        comfy_b = _make_fake_comfy(tmp_path / "b")
        monkeypatch.setenv("COMFY_PATH", str(comfy_a))
        result = backend.get_comfy_path(str(comfy_b))
        assert result == comfy_b.resolve()


# ---------------------------------------------------------------------------
# get_comfy_python (auto-detect candidates)
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestGetComfyPython:
    def test_explicit_flag_used(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        py = tmp_path / "explicit_python"
        py.write_text("# fake\n")
        result = backend.get_comfy_python(comfy, str(py))
        assert result == py.resolve()

    def test_explicit_missing_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        with pytest.raises(ComfyPathError):
            backend.get_comfy_python(comfy, str(tmp_path / "nope"))

    def test_env_var_used(self, tmp_path, monkeypatch):
        comfy = _make_fake_comfy(tmp_path / "comfy")
        py = tmp_path / "env_python"
        py.write_text("# fake\n")
        monkeypatch.setenv("COMFY_PYTHON", str(py))
        result = backend.get_comfy_python(comfy, None)
        assert result == py.resolve()

    def test_autodetect_venv(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        if sys.platform == "win32":
            venv_py = comfy / ".venv" / "Scripts" / "python.exe"
        else:
            venv_py = comfy / ".venv" / "bin" / "python"
        venv_py.parent.mkdir(parents=True)
        venv_py.write_text("# fake\n")
        result = backend.get_comfy_python(comfy, None)
        assert result == venv_py

    def test_autodetect_returns_none_when_no_candidates(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        result = backend.get_comfy_python(comfy, None)
        assert result is None


# ---------------------------------------------------------------------------
# derive_name
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestDeriveName:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://github.com/AHEKOT/ComfyUI_VNCCS.git", "ComfyUI_VNCCS"),
            ("https://github.com/AHEKOT/ComfyUI_VNCCS", "ComfyUI_VNCCS"),
            ("https://github.com/AHEKOT/ComfyUI_VNCCS/", "ComfyUI_VNCCS"),
            ("git@github.com:foo/bar.git", "bar"),
            ("ssh://git@github.com/foo/baz", "baz"),
            # Case-insensitive `.git` strip (R3 must-fix #4)
            ("http://example.com/foo/bar.GIT", "bar"),
            # Trailing whitespace inside the segment must be stripped
            ("http://example.com/foo/bar .git", "bar"),
            # Outer whitespace around the whole URL must be stripped
            (" http://example.com/foo/bar.git ", "bar"),
        ],
    )
    def test_common_urls(self, url, expected):
        assert custom_nodes_install.derive_name(url) == expected

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            custom_nodes_install.derive_name("/")


# ---------------------------------------------------------------------------
# run_install (subprocess mocked)
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunInstall:
    def test_already_installed_returns_skipped(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        existing = comfy / "custom_nodes" / "ExistingNode"
        existing.mkdir()
        result = custom_nodes_install.run_install(
            "https://github.com/foo/ExistingNode.git",
            comfy_path=str(comfy),
        )
        assert result["skipped"] is True
        assert result["restart_required"] is False
        assert "already installed" in result["reason"]

    def test_force_replaces_existing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        existing = comfy / "custom_nodes" / "ExistingNode"
        existing.mkdir()
        (existing / "old_file.txt").write_text("stale\n")

        captured: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured.append(list(cmd))
            target_dir = Path(cmd[-1])
            target_dir.mkdir(parents=True, exist_ok=True)
            return MagicMock(stdout="", stderr="", returncode=0)

        url = "https://github.com/foo/ExistingNode.git"
        with patch.object(custom_nodes_install, "run_subprocess", side_effect=fake_run):
            result = custom_nodes_install.run_install(
                url,
                comfy_path=str(comfy),
                force=True,
            )
        assert result["skipped"] is False
        # Old contents gone
        assert not (existing / "old_file.txt").exists()
        # Exact git-clone argv — catches dropping `--depth 1` or reordering
        # (R4 must-fix #6).
        expected_target = str(comfy / "custom_nodes" / "ExistingNode")
        assert captured[0] == ["git", "clone", "--depth", "1", url, expected_target]

    def test_install_with_requirements_runs_pip(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        py = tmp_path / "fake_python"
        py.write_text("# fake\n")
        monkeypatch.setenv("COMFY_PYTHON", str(py))

        commands_run: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            commands_run.append(list(cmd))
            if cmd[:2] == ["git", "clone"]:
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
                # Simulate a requirements.txt in the cloned repo
                (target_dir / "requirements.txt").write_text("typer>=0.15.0\n")
            return MagicMock(stdout="", stderr="", returncode=0)

        with patch.object(custom_nodes_install, "run_subprocess", side_effect=fake_run):
            result = custom_nodes_install.run_install(
                "https://github.com/foo/HasReqs.git",
                comfy_path=str(comfy),
            )
        assert result["deps_installed"] is True
        # Both git clone and pip install ran
        assert any(c[:2] == ["git", "clone"] for c in commands_run)
        # Pip invoked via the resolved comfy_python interpreter, NOT
        # sys.executable (R4 must-fix #7). Walk the pip argv and assert the
        # interpreter path is `py.resolve()`.
        pip_cmds = [
            c
            for c in commands_run
            if len(c) >= 3 and c[1:3] == ["-m", "pip"]
        ]
        assert pip_cmds, f"expected a `<python> -m pip` invocation, got: {commands_run}"
        assert Path(pip_cmds[0][0]) == py.resolve()

    def test_no_deps_skips_pip_install(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        py = tmp_path / "fake_python"
        py.write_text("# fake\n")
        monkeypatch.setenv("COMFY_PYTHON", str(py))

        commands_run: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            commands_run.append(list(cmd))
            if cmd[:2] == ["git", "clone"]:
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
                (target_dir / "requirements.txt").write_text("typer>=0.15.0\n")
            return MagicMock(stdout="", stderr="", returncode=0)

        with patch.object(custom_nodes_install, "run_subprocess", side_effect=fake_run):
            result = custom_nodes_install.run_install(
                "https://github.com/foo/HasReqs.git",
                comfy_path=str(comfy),
                no_deps=True,
            )
        assert result["deps_installed"] is False
        assert not any("pip" in c for c in commands_run)

    def test_no_python_warns_and_skips_pip(self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        # No python interpreter: no .venv, no env var

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "clone"]:
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
                (target_dir / "requirements.txt").write_text("typer>=0.15.0\n")
            return MagicMock(stdout="", stderr="", returncode=0)

        with patch.object(custom_nodes_install, "run_subprocess", side_effect=fake_run):
            result = custom_nodes_install.run_install(
                "https://github.com/foo/HasReqs.git",
                comfy_path=str(comfy),
            )
        assert result["deps_installed"] is False
        captured = capsys.readouterr()
        # Rich routes warnings to the captured stdout via Console.
        combined = (captured.out + captured.err).lower()
        assert "warning" in combined and "python" in combined

    def test_unsafe_name_rejected(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        with pytest.raises(ComfyError):
            custom_nodes_install.run_install(
                "https://github.com/foo/.git",
                name=".",
                comfy_path=str(comfy),
            )

    @pytest.mark.parametrize(
        "bad_name",
        [
            "..",
            ".",
            "../escape",
            "a/b",
            "a\\b",
            "foo/../bar",
            "foo/..",
        ],
    )
    def test_install_rejects_malicious_name(self, bad_name, tmp_path, monkeypatch):
        """R3 must-fix #2: `--name` must reject path separators / traversal."""
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        with pytest.raises(ComfyError):
            custom_nodes_install.run_install(
                "https://github.com/foo/Legit.git",
                name=bad_name,
                comfy_path=str(comfy),
            )

    def test_kitchen_sink_all_params(self, tmp_path, monkeypatch):
        """Per SWOT W1 (kitchen-sink test): exercise every parameter at once."""
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        py = tmp_path / "explicit_python"
        py.write_text("# fake\n")

        commands_run: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            commands_run.append(list(cmd))
            if cmd[:2] == ["git", "clone"]:
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
                (target_dir / "requirements.txt").write_text("\n")
            return MagicMock(stdout="", stderr="", returncode=0)

        with patch.object(custom_nodes_install, "run_subprocess", side_effect=fake_run):
            result = custom_nodes_install.run_install(
                "https://github.com/foo/Original.git",
                name="OverriddenName",
                comfy_path=str(comfy),
                python_path=str(py),
                no_deps=False,
                force=False,
            )
        assert result["name"] == "OverriddenName"
        assert result["path"].endswith("OverriddenName")
        assert result["deps_installed"] is True
        assert result["restart_required"] is True
        # Verify the explicit python interpreter (not auto-detected) was used.
        pip_cmds = [c for c in commands_run if "pip" in c]
        assert pip_cmds and str(py) in pip_cmds[0][0]


# ---------------------------------------------------------------------------
# run_list
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunList:
    def test_empty_returns_empty_list(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        assert custom_nodes_list.run_list(comfy_path=str(comfy)) == []

    def test_skips_non_directories(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        (comfy / "custom_nodes" / "loose_file.py").write_text("# example\n")
        (comfy / "custom_nodes" / "RealNode").mkdir()
        nodes = custom_nodes_list.run_list(comfy_path=str(comfy))
        assert [n["name"] for n in nodes] == ["RealNode"]

    def test_detects_requirements_and_git(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        node = comfy / "custom_nodes" / "WithReqs"
        node.mkdir()
        (node / "requirements.txt").write_text("\n")
        (node / ".git").mkdir()  # marker only — git_describe will fail safely
        nodes = custom_nodes_list.run_list(comfy_path=str(comfy))
        assert nodes[0]["has_requirements"] is True
        assert nodes[0]["is_git"] is True

    def test_iterdir_oserror_becomes_comfy_path_error(self, tmp_path, monkeypatch):
        """R3 must-fix #3: iterdir() failures must raise ComfyPathError
        with a clean message, not leak the raw OSError/PermissionError."""
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")

        real_iterdir = Path.iterdir

        def fake_iterdir(self):
            # Only fail for the custom_nodes dir, let everything else through.
            if self.name == "custom_nodes":
                raise PermissionError(f"simulated EACCES on {self}")
            return real_iterdir(self)

        with patch.object(Path, "iterdir", fake_iterdir):
            with pytest.raises(ComfyPathError) as exc:
                custom_nodes_list.run_list(comfy_path=str(comfy))
        assert "could not read" in exc.value.message.lower()
        assert "simulated EACCES" in (exc.value.detail or "")

    def test_ordering_is_alphabetic_regardless_of_creation_order(
        self, tmp_path, monkeypatch
    ):
        """R4 nice-to-fix #1: list must sort by name, not filesystem / creation order."""
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        # Create in deliberately non-alphabetic order.
        for name in ("zeta", "alpha", "mike", "bravo"):
            (comfy / "custom_nodes" / name).mkdir()
        nodes = custom_nodes_list.run_list(comfy_path=str(comfy))
        assert [n["name"] for n in nodes] == ["alpha", "bravo", "mike", "zeta"]

    def test_pycache_subdir_is_filtered(self, tmp_path, monkeypatch):
        """R4 nice-to-fix #2: a `__pycache__/` subdir of custom_nodes/ is ignored."""
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        (comfy / "custom_nodes" / "__pycache__").mkdir()
        (comfy / "custom_nodes" / "RealNode").mkdir()
        nodes = custom_nodes_list.run_list(comfy_path=str(comfy))
        assert [n["name"] for n in nodes] == ["RealNode"]


# ---------------------------------------------------------------------------
# run_update
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunUpdate:
    def test_name_and_all_mutex(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        with pytest.raises(ComfyError, match="not both"):
            custom_nodes_update.run_update(
                "Foo", all_nodes=True, comfy_path=str(comfy)
            )

    def test_neither_name_nor_all(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        with pytest.raises(ComfyError, match="--all"):
            custom_nodes_update.run_update(comfy_path=str(comfy))

    def test_unknown_name_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        with pytest.raises(ComfyError, match="not installed"):
            custom_nodes_update.run_update("Ghost", comfy_path=str(comfy))

    def test_non_git_node_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        node = comfy / "custom_nodes" / "Manual"
        node.mkdir()
        with pytest.raises(ComfyError, match="not a git checkout"):
            custom_nodes_update.run_update("Manual", comfy_path=str(comfy))

    def test_all_with_no_git_dirs_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        (comfy / "custom_nodes" / "Manual").mkdir()
        result = custom_nodes_update.run_update(all_nodes=True, comfy_path=str(comfy))
        assert result == []

    def test_already_up_to_date_skips_pip(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        node = comfy / "custom_nodes" / "Existing"
        node.mkdir()
        (node / ".git").mkdir()
        (node / "requirements.txt").write_text("\n")
        py = tmp_path / "p"
        py.write_text("# fake\n")
        monkeypatch.setenv("COMFY_PYTHON", str(py))

        commands_run: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            commands_run.append(list(cmd))
            # Return identical SHA for both pre- and post-pull rev-parse —
            # triggers the locale-independent "already up to date" detection.
            if cmd[:2] == ["git", "rev-parse"]:
                return MagicMock(stdout="abc1234\n", stderr="", returncode=0)
            return MagicMock(stdout="Already up to date.\n", stderr="", returncode=0)

        with patch.object(custom_nodes_update, "run_subprocess", side_effect=fake_run):
            result = custom_nodes_update.run_update(
                "Existing", comfy_path=str(comfy)
            )
        assert result[0]["already_up_to_date"] is True
        assert result[0]["deps_installed"] is False
        # Pip was NOT called (skipped because no actual update)
        assert not any("pip" in c for c in commands_run)

    def test_sha_change_means_not_up_to_date(self, tmp_path, monkeypatch):
        """R3 must-fix #5: pre/post SHA comparison is locale-independent.

        Different SHAs pre/post pull must set already_up_to_date=False even
        when git's stdout would have matched the old English-text heuristic
        (or, as here, is completely unrelated text from a translated locale).
        """
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        node = comfy / "custom_nodes" / "Advancing"
        node.mkdir()
        (node / ".git").mkdir()

        # Serve different SHAs for the two rev-parse calls (pre and post).
        sha_values = iter(["aaaa111", "bbbb222"])

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "rev-parse"]:
                return MagicMock(
                    stdout=next(sha_values) + "\n", stderr="", returncode=0
                )
            # git pull output in a non-English locale would normally break
            # the old text heuristic — use a deliberately unparseable string.
            return MagicMock(
                stdout="Déjà à jour.\n", stderr="", returncode=0
            )

        with patch.object(custom_nodes_update, "run_subprocess", side_effect=fake_run):
            result = custom_nodes_update.run_update(
                "Advancing", comfy_path=str(comfy)
            )
        assert result[0]["already_up_to_date"] is False

    def test_sha_identical_means_up_to_date(self, tmp_path, monkeypatch):
        """R3 must-fix #5: identical pre/post SHAs ⇒ already_up_to_date=True
        even when git's stdout is translated (non-English locale)."""
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        node = comfy / "custom_nodes" / "Steady"
        node.mkdir()
        (node / ".git").mkdir()

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "rev-parse"]:
                return MagicMock(stdout="deadbeef\n", stderr="", returncode=0)
            return MagicMock(stdout="Déjà à jour.\n", stderr="", returncode=0)

        with patch.object(custom_nodes_update, "run_subprocess", side_effect=fake_run):
            result = custom_nodes_update.run_update(
                "Steady", comfy_path=str(comfy)
            )
        assert result[0]["already_up_to_date"] is True

    def test_all_continues_after_per_node_failure(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        for n in ("A", "B", "C"):
            d = comfy / "custom_nodes" / n
            d.mkdir()
            (d / ".git").mkdir()

        def fake_run(cmd, **kwargs):
            cwd_str = str(kwargs.get("cwd", ""))
            if "B" in cwd_str:
                raise ComfySubprocessError(
                    "git pull failed", detail="upstream unreachable"
                )
            return MagicMock(stdout="Already up to date.\n", stderr="", returncode=0)

        with patch.object(custom_nodes_update, "run_subprocess", side_effect=fake_run):
            results = custom_nodes_update.run_update(
                all_nodes=True, comfy_path=str(comfy)
            )
        assert len(results) == 3
        assert any("error" in r for r in results)
        assert sum(1 for r in results if "error" not in r) == 2


# ---------------------------------------------------------------------------
# run_remove
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunRemove:
    def test_requires_yes(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        (comfy / "custom_nodes" / "Foo").mkdir()
        with pytest.raises(ComfyError, match="confirmation"):
            custom_nodes_remove.run_remove("Foo", comfy_path=str(comfy))

    def test_run_remove_without_yes_leaves_directory(self, tmp_path, monkeypatch):
        """R4 must-fix #9: after refusing (no --yes), the target dir must
        still exist on disk. Catches a regression where the --yes check is
        moved after rmtree."""
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        target = comfy / "custom_nodes" / "Foo"
        target.mkdir()
        (target / "sentinel.txt").write_text("still here\n")

        with pytest.raises(ComfyError):
            custom_nodes_remove.run_remove("Foo", comfy_path=str(comfy))

        # Filesystem-state assertion: the dir AND its contents survived.
        assert target.exists()
        assert (target / "sentinel.txt").read_text() == "still here\n"

    def test_unknown_name_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        with pytest.raises(ComfyError, match="not installed"):
            custom_nodes_remove.run_remove("Ghost", comfy_path=str(comfy), yes=True)

    @pytest.mark.parametrize(
        "bad",
        [
            "..",
            ".",
            "../escape",
            "a/b",
            "a\\b",
            # R4 nice-to-fix #5: absolute paths + empty string
            "/etc",
            "C:/Windows",
            "",
        ],
    )
    def test_path_traversal_rejected(self, bad, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        with pytest.raises(ComfyError, match="(?i)invalid"):
            custom_nodes_remove.run_remove(bad, comfy_path=str(comfy), yes=True)

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="symlink creation on Windows requires elevated privileges or dev mode",
    )
    def test_symlink_target_refused(self, tmp_path, monkeypatch):
        """R3 must-fix #1: if the target is a symlink, remove must refuse
        rather than follow it and rmtree its contents."""
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        # Something outside custom_nodes/ that the symlink will point at.
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "precious.txt").write_text("do not delete\n")

        link = comfy / "custom_nodes" / "EvilLink"
        link.symlink_to(outside, target_is_directory=True)

        with pytest.raises(ComfyError, match="(?i)symlink"):
            custom_nodes_remove.run_remove(
                "EvilLink", comfy_path=str(comfy), yes=True
            )

        # The link and — most importantly — the outside directory survived.
        assert link.is_symlink()
        assert (outside / "precious.txt").exists()

    def test_happy_path_removes_dir(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        comfy = _make_fake_comfy(tmp_path / "comfy")
        target = comfy / "custom_nodes" / "Foo"
        target.mkdir()
        (target / "module.py").write_text("# fake\n")
        result = custom_nodes_remove.run_remove("Foo", comfy_path=str(comfy), yes=True)
        assert not target.exists()
        assert result["removed"] is True
        assert result["restart_required"] is True


# ---------------------------------------------------------------------------
# Backend run_subprocess error surface (per SWOT W2 / W6)
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestRunSubprocess:
    def test_nonzero_exit_surfaces_stderr(self, tmp_path):
        """Mocked CalledProcessError-equivalent: non-zero exit must raise
        ComfySubprocessError with stderr in detail (matches pandoc's run_pandoc
        pattern from the SWOT W2 hardening)."""

        def fake_run(*args, **kwargs):
            return MagicMock(
                returncode=1,
                stdout="",
                stderr="fatal: repository not found",
            )

        with patch.object(backend.subprocess, "run", side_effect=fake_run):
            with pytest.raises(ComfySubprocessError) as exc:
                backend.run_subprocess(
                    ["git", "clone", "https://example.com/none.git", "/tmp/x"],
                    op_name="git clone",
                )
        assert "exit 1" in exc.value.message
        assert "repository not found" in (exc.value.detail or "")

    def test_command_not_found(self):
        with patch.object(backend.subprocess, "run", side_effect=FileNotFoundError("no such file")):
            with pytest.raises(ComfySubprocessError) as exc:
                backend.run_subprocess(["nonexistent_binary_xyz"], op_name="probe")
        assert "command not found" in exc.value.message.lower()

    def test_timeout_surfaces_clear_error(self):
        """R4 must-fix #10: subprocess.TimeoutExpired must translate to
        ComfySubprocessError with 'timed out' in the message and original
        info in detail."""
        import subprocess as _sp

        def fake_run(*args, **kwargs):
            raise _sp.TimeoutExpired(cmd=["git"], timeout=1.0)

        with patch.object(backend.subprocess, "run", side_effect=fake_run):
            with pytest.raises(ComfySubprocessError) as exc:
                backend.run_subprocess(
                    ["git", "--version"], timeout=1.0, op_name="test"
                )
        assert "timed out" in exc.value.message.lower()
        # Original TimeoutExpired repr includes the command + timeout value.
        assert exc.value.detail and "1" in exc.value.detail


# ---------------------------------------------------------------------------
# safe_rmtree (read-only handler)
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestSafeRmtree:
    def test_safe_rmtree_handles_readonly(self, tmp_path):
        """R4 must-fix #8: safe_rmtree must succeed when the tree contains
        a read-only file (the `_rmtree_handle_readonly` callback must fire).

        On POSIX the parent-dir write bit usually lets the owner unlink
        anyway, but we still want to verify the callback is wired up and
        doesn't error. On Windows this is the primary failure mode.
        """
        import os

        parent = tmp_path / "to_delete"
        parent.mkdir()
        ro_file = parent / "readonly.txt"
        ro_file.write_text("locked\n")
        os.chmod(ro_file, 0o444)
        try:
            backend.safe_rmtree(parent)
        finally:
            # Best-effort cleanup if the test fails and the file survives.
            if ro_file.exists():
                os.chmod(ro_file, 0o644)
        assert not parent.exists()

    def test_safe_rmtree_no_op_on_missing_path(self, tmp_path):
        """Missing path is a no-op, not an error."""
        target = tmp_path / "nope"
        backend.safe_rmtree(target)  # should not raise
        assert not target.exists()
