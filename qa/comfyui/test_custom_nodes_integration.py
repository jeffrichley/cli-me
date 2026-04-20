"""Tier 2 integration tests for the custom-nodes command group.

These exercise REAL git operations (no network) by creating local bare
repos in tmp_path and pointing the install/update commands at them.
Skips cleanly when git is missing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

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


pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def git_path() -> str:
    """git binary path or skip the suite if git is missing."""
    p = shutil.which("git")
    if p is None:
        pytest.skip("git not on PATH; cannot exercise real git operations")
    return p


@pytest.fixture
def fake_comfy(tmp_path: Path) -> Path:
    """A minimal fake ComfyUI install root with custom_nodes/ + main.py."""
    root = tmp_path / "ComfyUI"
    root.mkdir()
    (root / "custom_nodes").mkdir()
    (root / "main.py").write_text("# fake comfy entry point\n", encoding="utf-8")
    return root


def _git(args: list[str], cwd: Path) -> None:
    """Run git in `cwd`; raise on non-zero. Used by fixtures, not tests."""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {args} failed in {cwd}:\n{result.stderr or result.stdout}"
        )


@pytest.fixture
def upstream_repo(tmp_path: Path, git_path: str) -> Path:
    """A real bare-repo "remote" sitting in tmp_path/upstream.git.

    Creates a working repo, commits a sample custom-node module + (optionally
    in derived fixtures) a requirements.txt, then converts it to bare so the
    install command can `git clone` from it. Returns the bare-repo path.
    """
    work = tmp_path / "upstream_work"
    work.mkdir()
    _git(["init", "-q", "-b", "main"], work)
    _git(["config", "user.email", "test@example.com"], work)
    _git(["config", "user.name", "Test"], work)
    (work / "__init__.py").write_text(
        'NODE_CLASS_MAPPINGS = {}\nNODE_DISPLAY_NAME_MAPPINGS = {}\n',
        encoding="utf-8",
    )
    (work / "README.md").write_text("# Test custom node\n", encoding="utf-8")
    _git(["add", "-A"], work)
    _git(["commit", "-q", "-m", "initial"], work)

    bare = tmp_path / "upstream.git"
    _git(["clone", "--bare", "-q", str(work), str(bare)], tmp_path)
    return bare


@pytest.fixture
def upstream_repo_with_reqs(tmp_path: Path, git_path: str) -> Path:
    """Like upstream_repo but the working tree contains a requirements.txt."""
    work = tmp_path / "upstream_reqs_work"
    work.mkdir()
    _git(["init", "-q", "-b", "main"], work)
    _git(["config", "user.email", "test@example.com"], work)
    _git(["config", "user.name", "Test"], work)
    (work / "__init__.py").write_text("NODE_CLASS_MAPPINGS = {}\n", encoding="utf-8")
    # A trivially-satisfiable requirement so pip install doesn't actually
    # touch the network. `pip` is universally already installed.
    (work / "requirements.txt").write_text("pip\n", encoding="utf-8")
    _git(["add", "-A"], work)
    _git(["commit", "-q", "-m", "initial"], work)

    bare = tmp_path / "upstream_reqs.git"
    _git(["clone", "--bare", "-q", str(work), str(bare)], tmp_path)
    return bare


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


class TestInstallReal:
    def test_clones_real_repo(
        self, fake_comfy, upstream_repo, monkeypatch
    ):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        result = custom_nodes_install.run_install(
            f"file://{upstream_repo.as_posix()}",
            name="TestNode",
            comfy_path=str(fake_comfy),
        )
        target = fake_comfy / "custom_nodes" / "TestNode"
        assert target.is_dir()
        assert (target / "__init__.py").exists()
        assert (target / ".git").exists()
        assert result["restart_required"] is True
        assert result["deps_installed"] is False  # No requirements.txt

    def test_idempotent_skip(
        self, fake_comfy, upstream_repo, monkeypatch
    ):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        custom_nodes_install.run_install(
            f"file://{upstream_repo.as_posix()}",
            name="TwiceNode",
            comfy_path=str(fake_comfy),
        )
        result = custom_nodes_install.run_install(
            f"file://{upstream_repo.as_posix()}",
            name="TwiceNode",
            comfy_path=str(fake_comfy),
        )
        assert result["skipped"] is True
        assert "already installed" in result["reason"]

    def test_force_reclones(
        self, fake_comfy, upstream_repo, monkeypatch
    ):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        custom_nodes_install.run_install(
            f"file://{upstream_repo.as_posix()}",
            name="ForceNode",
            comfy_path=str(fake_comfy),
        )
        target = fake_comfy / "custom_nodes" / "ForceNode"
        # Add a stray file; force should wipe it.
        (target / "stray.txt").write_text("delete me\n")
        result = custom_nodes_install.run_install(
            f"file://{upstream_repo.as_posix()}",
            name="ForceNode",
            comfy_path=str(fake_comfy),
            force=True,
        )
        assert result["skipped"] is False
        assert not (target / "stray.txt").exists()

    def test_requirements_install_uses_real_python(
        self, fake_comfy, upstream_repo_with_reqs, monkeypatch
    ):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        # Use the test runner's own Python — it definitely has `pip` already
        # so the install of the trivial `pip` requirement is a no-op fast-path.
        result = custom_nodes_install.run_install(
            f"file://{upstream_repo_with_reqs.as_posix()}",
            name="HasReqsNode",
            comfy_path=str(fake_comfy),
            python_path=sys.executable,
        )
        assert result["deps_installed"] is True

    def test_no_deps_skips_pip(
        self, fake_comfy, upstream_repo_with_reqs, monkeypatch
    ):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        monkeypatch.delenv("COMFY_PYTHON", raising=False)
        result = custom_nodes_install.run_install(
            f"file://{upstream_repo_with_reqs.as_posix()}",
            name="NoDepsNode",
            comfy_path=str(fake_comfy),
            python_path=sys.executable,
            no_deps=True,
        )
        assert result["deps_installed"] is False

    def test_bad_repo_url_surfaces_git_error(self, fake_comfy, monkeypatch):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        with pytest.raises(ComfySubprocessError) as exc:
            custom_nodes_install.run_install(
                "file:///definitely/not/a/repo/path/zzz.git",
                name="BadNode",
                comfy_path=str(fake_comfy),
            )
        # Per SWOT W2: subprocess error must surface stderr (not a Python traceback)
        assert "git clone" in exc.value.message
        # git's actual error text shows up in detail
        assert exc.value.detail


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListReal:
    def test_lists_installed_nodes_with_git_metadata(
        self, fake_comfy, upstream_repo, monkeypatch
    ):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        custom_nodes_install.run_install(
            f"file://{upstream_repo.as_posix()}",
            name="ListedNode",
            comfy_path=str(fake_comfy),
        )
        # Add a non-git node alongside.
        (fake_comfy / "custom_nodes" / "Manual").mkdir()
        (fake_comfy / "custom_nodes" / "Manual" / "node.py").write_text("# manual\n")

        nodes = custom_nodes_list.run_list(comfy_path=str(fake_comfy))
        names = [n["name"] for n in nodes]
        assert "ListedNode" in names
        assert "Manual" in names

        listed = next(n for n in nodes if n["name"] == "ListedNode")
        assert listed["is_git"] is True
        # Real git metadata populated
        assert "commit" in listed
        assert len(listed["commit"]) >= 4

        manual = next(n for n in nodes if n["name"] == "Manual")
        assert manual["is_git"] is False


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateReal:
    def test_already_up_to_date(
        self, fake_comfy, upstream_repo, monkeypatch
    ):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        custom_nodes_install.run_install(
            f"file://{upstream_repo.as_posix()}",
            name="UpToDateNode",
            comfy_path=str(fake_comfy),
        )
        results = custom_nodes_update.run_update(
            "UpToDateNode", comfy_path=str(fake_comfy)
        )
        assert results[0]["already_up_to_date"] is True
        assert results[0]["deps_installed"] is False

    def test_updates_when_upstream_advances(
        self, tmp_path, fake_comfy, upstream_repo, monkeypatch
    ):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        # Install at HEAD
        custom_nodes_install.run_install(
            f"file://{upstream_repo.as_posix()}",
            name="AdvancingNode",
            comfy_path=str(fake_comfy),
        )
        # Advance the bare repo by pushing a new commit from a fresh worktree
        work = tmp_path / "upstream_advance"
        _git(["clone", "-q", str(upstream_repo), str(work)], tmp_path)
        _git(["config", "user.email", "test@example.com"], work)
        _git(["config", "user.name", "Test"], work)
        (work / "new_feature.py").write_text("# new\n")
        _git(["add", "-A"], work)
        _git(["commit", "-q", "-m", "feature"], work)
        _git(["push", "-q"], work)

        results = custom_nodes_update.run_update(
            "AdvancingNode", comfy_path=str(fake_comfy)
        )
        assert results[0]["already_up_to_date"] is False
        assert (
            fake_comfy / "custom_nodes" / "AdvancingNode" / "new_feature.py"
        ).exists()


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


class TestRemoveReal:
    def test_removes_real_directory(
        self, fake_comfy, upstream_repo, monkeypatch
    ):
        monkeypatch.delenv("COMFY_PATH", raising=False)
        custom_nodes_install.run_install(
            f"file://{upstream_repo.as_posix()}",
            name="DeleteMe",
            comfy_path=str(fake_comfy),
        )
        target = fake_comfy / "custom_nodes" / "DeleteMe"
        assert target.exists()

        result = custom_nodes_remove.run_remove(
            "DeleteMe", comfy_path=str(fake_comfy), yes=True
        )
        assert not target.exists()
        assert result["removed"] is True
