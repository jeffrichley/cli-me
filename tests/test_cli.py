import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from cli_me.main import app


runner = CliRunner()


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Set up a fake skill-repo and point the CLI at it."""
    repo = tmp_path / "skill-repo"
    gimp = repo / "gimp"
    gimp.mkdir(parents=True)
    (gimp / "SKILL.md").write_text(
        "---\nname: gimp\ndescription: Image editing\n---\n\n# GIMP\n"
    )
    scripts = gimp / "scripts"
    scripts.mkdir()
    (scripts / "pyproject.toml").write_text(
        '[project]\nname = "gimp-cli"\nversion = "0.1.0"\n'
        'requires-python = ">=3.12"\ndependencies = ["typer>=0.15.0"]\n'
    )
    (scripts / "gimp_cli.py").write_text("import typer\n")
    refs = gimp / "references"
    refs.mkdir()
    (refs / "index.md").write_text("# Wiki\n")

    registry = {
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
            }
        ]
    }
    (repo / "registry.json").write_text(json.dumps(registry))

    monkeypatch.setenv("CLIME_SKILL_REPO", str(repo))
    return repo


def test_list_skills(fake_repo):
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "gimp" in result.output


def test_list_by_category(fake_repo):
    result = runner.invoke(app, ["list", "--category", "image"])
    assert result.exit_code == 0
    assert "gimp" in result.output


def test_list_by_category_no_match(fake_repo):
    result = runner.invoke(app, ["list", "--category", "audio"])
    assert result.exit_code == 0
    # Should not contain any skill data when category doesn't match
    assert "gimp" not in result.output
    assert "image-editing" not in result.output


def test_search(fake_repo):
    result = runner.invoke(app, ["search", "pod"])
    assert result.exit_code == 0
    assert "gimp" in result.output


def test_search_no_results(fake_repo):
    result = runner.invoke(app, ["search", "nonexistent"])
    assert result.exit_code == 0
    # Should not contain any skill names when nothing matches
    assert "gimp" not in result.output


def test_info(fake_repo):
    result = runner.invoke(app, ["info", "gimp"])
    assert result.exit_code == 0
    assert "gimp" in result.output
    assert "image-editing" in result.output


def test_info_not_found(fake_repo):
    result = runner.invoke(app, ["info", "nonexistent"])
    assert result.exit_code == 1


def test_install_to_project(fake_repo, tmp_path):
    project = tmp_path / "my-project"
    project.mkdir()
    result = runner.invoke(app, ["install", "gimp", "--project", str(project)])
    assert result.exit_code == 0
    assert (project / ".claude" / "skills" / "gimp" / "SKILL.md").exists()


def test_install_not_found(fake_repo, tmp_path):
    project = tmp_path / "my-project"
    project.mkdir()
    result = runner.invoke(app, ["install", "nope", "--project", str(project)])
    assert result.exit_code == 1


def test_uninstall(fake_repo, tmp_path):
    project = tmp_path / "my-project"
    project.mkdir()
    runner.invoke(app, ["install", "gimp", "--project", str(project)])
    result = runner.invoke(app, ["uninstall", "gimp", "--project", str(project)])
    assert result.exit_code == 0
    assert not (project / ".claude" / "skills" / "gimp").exists()


def test_registry_add(fake_repo):
    result = runner.invoke(app, [
        "registry", "add",
        "--name", "blender",
        "--description", "3D modeling CLI",
        "--category", "3d",
        "--tags", "3d,modeling",
        "--version", "0.1.0",
    ])
    assert result.exit_code == 0
    assert "blender" in result.output

    # Verify it's persisted
    data = json.loads((fake_repo / "registry.json").read_text())
    names = [s["name"] for s in data["skills"]]
    assert "blender" in names


def test_registry_add_duplicate(fake_repo):
    result = runner.invoke(app, [
        "registry", "add",
        "--name", "gimp",
        "--description", "duplicate",
    ])
    assert result.exit_code == 1


def test_registry_remove(fake_repo):
    result = runner.invoke(app, ["registry", "remove", "gimp"])
    assert result.exit_code == 0

    data = json.loads((fake_repo / "registry.json").read_text())
    names = [s["name"] for s in data["skills"]]
    assert "gimp" not in names


def test_registry_remove_not_found(fake_repo):
    result = runner.invoke(app, ["registry", "remove", "nonexistent"])
    assert result.exit_code == 1


def test_registry_update(fake_repo):
    result = runner.invoke(app, [
        "registry", "update", "gimp",
        "--description", "Updated description",
        "--version", "0.2.0",
    ])
    assert result.exit_code == 0

    data = json.loads((fake_repo / "registry.json").read_text())
    skill = next(s for s in data["skills"] if s["name"] == "gimp")
    assert skill["description"] == "Updated description"
    assert skill["version"] == "0.2.0"


def test_registry_update_not_found(fake_repo):
    result = runner.invoke(app, [
        "registry", "update", "nonexistent",
        "--description", "nope",
    ])
    assert result.exit_code == 1
