import json
import os
import pytest
from pathlib import Path
from cli_me.installer import Installer


@pytest.fixture
def skill_repo(tmp_path):
    """Create a fake skill-repo with one skill."""
    repo = tmp_path / "skill-repo"
    gimp = repo / "gimp"
    gimp.mkdir(parents=True)

    # SKILL.md
    (gimp / "SKILL.md").write_text(
        "---\nname: gimp\ndescription: Image editing\n---\n\n# GIMP\n"
    )

    # scripts/
    scripts = gimp / "scripts"
    scripts.mkdir()
    (scripts / "pyproject.toml").write_text(
        '[project]\nname = "gimp-cli"\nversion = "0.1.0"\n'
        'requires-python = ">=3.12"\ndependencies = ["typer>=0.15.0"]\n'
    )
    (scripts / "gimp_cli.py").write_text("import typer\napp = typer.Typer()\n")

    # references/
    refs = gimp / "references"
    refs.mkdir()
    (refs / "index.md").write_text("# GIMP Wiki\n")
    (refs / "log.md").write_text("# Learning Log\n")

    # registry.json
    registry = {
        "skills": [
            {
                "name": "gimp",
                "description": "Image editing CLI for GIMP",
                "category": "image",
                "tags": ["image-editing"],
                "version": "0.1.0",
                "software_url": "https://www.gimp.org",
                "source_repo": "https://gitlab.gnome.org/GNOME/gimp",
                "dependencies": [],
            }
        ]
    }
    (repo / "registry.json").write_text(json.dumps(registry))
    return repo


@pytest.fixture
def target_project(tmp_path):
    return tmp_path / "my-project"


def test_install_to_project(skill_repo, target_project):
    installer = Installer(skill_repo)
    dest = installer.install("gimp", target_project, global_install=False)

    expected = target_project / ".claude" / "skills" / "gimp"
    assert dest == expected
    assert (expected / "SKILL.md").exists()
    assert (expected / "scripts" / "gimp_cli.py").exists()
    assert (expected / "references" / "index.md").exists()


def test_install_to_global(skill_repo, tmp_path):
    global_dir = tmp_path / "fake-home" / ".claude"
    installer = Installer(skill_repo)
    dest = installer.install("gimp", global_dir=global_dir, global_install=True)

    expected = global_dir / "skills" / "gimp"
    assert dest == expected
    assert (expected / "SKILL.md").exists()


def test_install_nonexistent_skill(skill_repo, target_project):
    installer = Installer(skill_repo)
    with pytest.raises(ValueError, match="not found"):
        installer.install("nonexistent", target_project, global_install=False)


def test_install_already_exists(skill_repo, target_project):
    installer = Installer(skill_repo)
    installer.install("gimp", target_project, global_install=False)
    with pytest.raises(FileExistsError, match="already installed"):
        installer.install("gimp", target_project, global_install=False)


def test_install_force_overwrites(skill_repo, target_project):
    installer = Installer(skill_repo)
    installer.install("gimp", target_project, global_install=False)
    # Modify installed file to verify overwrite
    installed = target_project / ".claude" / "skills" / "gimp" / "SKILL.md"
    installed.write_text("modified")
    installer.install("gimp", target_project, global_install=False, force=True)
    assert "modified" not in installed.read_text()


def test_uninstall_from_project(skill_repo, target_project):
    installer = Installer(skill_repo)
    installer.install("gimp", target_project, global_install=False)
    installer.uninstall("gimp", target_project, global_install=False)
    assert not (target_project / ".claude" / "skills" / "gimp").exists()


def test_uninstall_not_installed(skill_repo, target_project):
    installer = Installer(skill_repo)
    with pytest.raises(FileNotFoundError, match="not installed"):
        installer.uninstall("gimp", target_project, global_install=False)


def test_list_installed(skill_repo, target_project):
    installer = Installer(skill_repo)
    installer.install("gimp", target_project, global_install=False)
    installed = installer.list_installed(target_project, global_install=False)
    assert "gimp" in installed
