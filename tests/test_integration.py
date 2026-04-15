"""Integration test: create a skill in skill-repo, install it, verify structure."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from cli_me.main import app
from cli_me.registry import Registry


runner = CliRunner()


@pytest.fixture
def full_repo(tmp_path, monkeypatch):
    """Create a realistic skill-repo with a complete skill."""
    repo = tmp_path / "skill-repo"

    # Create a complete skill following the spec structure
    gimp = repo / "gimp"
    gimp.mkdir(parents=True)

    (gimp / "SKILL.md").write_text(
        "---\n"
        "name: gimp\n"
        "description: Image editing CLI for GIMP. Use when user asks to edit images,\n"
        "  remove backgrounds, batch process graphics, or prepare artwork for print.\n"
        "---\n\n"
        "# GIMP — cli-me skill\n\n"
        "## CLI Commands\n\n"
        "Run commands via:\n"
        "```bash\n"
        "uv run scripts/gimp_cli.py <command>\n"
        "```\n\n"
        "## After Completing Your Task\n\n"
        "Update references/ with what you learned.\n"
    )

    scripts = gimp / "scripts"
    scripts.mkdir()
    (scripts / "pyproject.toml").write_text(
        '[project]\nname = "gimp-cli"\nversion = "0.1.0"\n'
        'description = "Agent-native CLI for GIMP"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["typer>=0.15.0"]\n\n'
        '[project.scripts]\ngimp-cli = "gimp_cli:app"\n'
    )
    (scripts / "gimp_cli.py").write_text(
        'import typer\n\napp = typer.Typer()\n\n'
        '@app.command()\ndef version():\n    typer.echo("GIMP CLI 0.1.0")\n\n'
        'if __name__ == "__main__":\n    app()\n'
    )

    refs = gimp / "references"
    refs.mkdir()
    (refs / "index.md").write_text("# GIMP Knowledge Base\n\n- [Log](log.md)\n")
    (refs / "log.md").write_text("# Learning Log\n\n---\n\n"
                                  "**2026-04-14** — Initial scaffold.\n")
    (refs / "gotchas.md").write_text("# Gotchas\n\nNone yet.\n")

    sa = refs / "source-analysis"
    sa.mkdir()
    (sa / "analyzed-version.md").write_text(
        "# Analyzed Version\n\n**Current:** GIMP 3.0.2 (commit abc123)\n"
    )
    (sa / "api-surface.md").write_text("# API Surface\n\nPython-Fu 3, Script-Fu\n")
    (sa / "cli-interface.md").write_text("# CLI Interface\n\ngimp -i --batch-interpreter\n")
    (sa / "internal-architecture.md").write_text("# Internal Architecture\n\nGEGL-based.\n")
    (sa / "key-functions.md").write_text("# Key Functions\n\n## color-to-alpha\n")
    (sa / "changelog.md").write_text("# Changelog\n\nNo version updates yet.\n")

    techniques = refs / "techniques"
    techniques.mkdir()
    (techniques / "background-removal.md").write_text(
        "# Background Removal\n\n## When to Use\nPOD graphics.\n\n"
        "## CLI Commands\n```bash\nuv run scripts/gimp_cli.py remove-bg\n```\n\n"
        "## Sources\n- [GIMP docs](https://docs.gimp.org)\n"
    )

    # Registry
    registry = {
        "skills": [
            {
                "name": "gimp",
                "description": "Image editing CLI for GIMP",
                "category": "image",
                "tags": ["image-editing", "graphics", "pod", "background-removal"],
                "version": "0.1.0",
                "software_url": "https://www.gimp.org",
                "source_repo": "https://gitlab.gnome.org/GNOME/gimp",
                "dependencies": [],
            }
        ]
    }
    (repo / "registry.json").write_text(json.dumps(registry, indent=2))

    monkeypatch.setenv("CLIME_SKILL_REPO", str(repo))
    return repo


def test_full_install_workflow(full_repo, tmp_path):
    """Install a skill, verify all files copied, uninstall, verify clean."""
    project = tmp_path / "my-project"
    project.mkdir()

    # Install
    result = runner.invoke(app, ["install", "gimp", "--project", str(project)])
    assert result.exit_code == 0

    installed = project / ".claude" / "skills" / "gimp"
    assert installed.exists()
    assert (installed / "SKILL.md").exists()
    assert (installed / "scripts" / "pyproject.toml").exists()
    assert (installed / "scripts" / "gimp_cli.py").exists()
    assert (installed / "references" / "index.md").exists()
    assert (installed / "references" / "log.md").exists()
    assert (installed / "references" / "source-analysis" / "analyzed-version.md").exists()
    assert (installed / "references" / "techniques" / "background-removal.md").exists()

    # Verify SKILL.md content has key structural elements
    skill_content = (installed / "SKILL.md").read_text()
    assert "name: gimp" in skill_content
    assert "After Completing Your Task" in skill_content

    # Info command returns skill data
    result = runner.invoke(app, ["info", "gimp"])
    assert result.exit_code == 0
    assert "gimp" in result.output
    assert "image-editing" in result.output

    # Search finds it by tag
    result = runner.invoke(app, ["search", "pod"])
    assert result.exit_code == 0
    assert "gimp" in result.output

    # Uninstall removes all files
    result = runner.invoke(app, ["uninstall", "gimp", "--project", str(project)])
    assert result.exit_code == 0
    assert not installed.exists()


def test_registry_add_and_install(full_repo, tmp_path):
    """Add a new skill to registry, create its folder, install it."""
    # Create a minimal new skill
    blender = full_repo / "blender"
    blender.mkdir()
    (blender / "SKILL.md").write_text("---\nname: blender\ndescription: 3D CLI\n---\n")

    # Add to registry
    reg = Registry(full_repo / "registry.json")
    reg.add({
        "name": "blender",
        "description": "3D modeling CLI for Blender",
        "category": "3d",
        "tags": ["3d", "modeling"],
        "version": "0.1.0",
        "software_url": "https://www.blender.org",
        "source_repo": "https://github.com/blender/blender",
        "dependencies": [],
    })
    reg.save()

    # Verify both skills show in list
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "blender" in result.output
    assert "gimp" in result.output

    # Install the new skill
    project = tmp_path / "project2"
    project.mkdir()
    result = runner.invoke(app, ["install", "blender", "--project", str(project)])
    assert result.exit_code == 0
    assert (project / ".claude" / "skills" / "blender" / "SKILL.md").exists()
