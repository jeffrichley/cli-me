# cli-me Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the cli-me framework — a meta-skill that generates Claude Code skills for GUI software, an installer CLI, and the repo scaffolding that ties it all together.

**Architecture:** Monorepo with three components: (1) a meta-skill at `.claude/skills/cli-me-meta/` that drives skill creation through research, scaffolding, implementation, and testing phases; (2) a `skill-repo/` directory holding generated skills, each with a SKILL.md, Typer CLI scripts, and a self-evolving LLM wiki; (3) a Typer-based installer CLI registered as `clime`/`cli-me` that copies skills to project or global Claude directories.

**Tech Stack:** Python 3.12+, Typer (CLI framework), uv (package runner), Claude Code skills (SKILL.md + scripts/ + references/)

**Spec:** `docs/superpowers/specs/2026-04-14-cli-me-design.md`

---

## File Map

### Repo Config
- Modify: `pyproject.toml` — add Typer dependency, entry points
- Modify: `.gitignore` — add tmp/source-analysis/

### Installer CLI
- Create: `cli_me/__init__.py` — package init
- Create: `cli_me/main.py` — Typer app with install, list, search, info, uninstall commands
- Create: `cli_me/registry.py` — registry.json read/search/filter logic
- Create: `cli_me/installer.py` — copy skill folders to target directories
- Create: `tests/test_cli.py` — CLI command tests
- Create: `tests/test_registry.py` — registry search/filter tests
- Create: `tests/test_installer.py` — install/uninstall file copy tests

### Skill Repo
- Create: `skill-repo/registry.json` — empty initial registry

### Meta-Skill
- Create: `.claude/skills/cli-me-meta/SKILL.md` — the meta-skill instructions
- Create: `.claude/skills/cli-me-meta/references/skill-template.md` — template for generated SKILL.md files
- Create: `.claude/skills/cli-me-meta/references/wiki-template.md` — template for wiki initialization
- Create: `.claude/skills/cli-me-meta/references/technique-page-template.md` — template for technique pages
- Create: `.claude/skills/cli-me-meta/references/typer-cli-template.md` — template for Typer CLI scaffolding
- Create: `.claude/skills/cli-me-meta/references/write-back-instructions.md` — standard write-back section
- Create: `.claude/skills/cli-me-meta/references/meta-wiki/index.md` — meta-skill's own wiki index
- Create: `.claude/skills/cli-me-meta/references/meta-wiki/log.md` — meta-skill's own learning log

---

## Task 1: Repo Scaffolding

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `skill-repo/registry.json`
- Create: `cli_me/__init__.py`

- [ ] **Step 1: Update pyproject.toml with dependencies and entry points**

```toml
[project]
name = "cli-me"
version = "0.1.0"
description = "Agent-native skills for GUI software — build, install, and evolve Claude Code skills"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
]

[project.scripts]
clime = "cli_me.main:main"
"cli-me" = "cli_me.main:main"

[dependency-groups]
dev = [
    "pytest>=8.0.0",
]
```

- [ ] **Step 2: Update .gitignore**

Append to existing `.gitignore`:

```
# Source analysis working directory
tmp/source-analysis/
```

- [ ] **Step 3: Create empty registry**

Create `skill-repo/registry.json`:

```json
{
  "skills": []
}
```

- [ ] **Step 4: Create cli_me package init**

Create `cli_me/__init__.py`:

```python
"""cli-me: Agent-native skills for GUI software."""
```

- [ ] **Step 5: Verify uv recognizes the project**

Run: `uv sync`
Expected: dependencies install, no errors

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore skill-repo/registry.json cli_me/__init__.py
git commit -m "scaffold: init repo with pyproject.toml, registry, and cli_me package"
```

---

## Task 2: Registry Module

**Files:**
- Create: `cli_me/registry.py`
- Create: `tests/test_registry.py`

- [ ] **Step 1: Write failing tests for registry loading and search**

Create `tests/test_registry.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cli_me.registry'`

- [ ] **Step 3: Implement registry module**

Create `cli_me/registry.py`:

```python
"""Skill registry: load, search, and manage skill-repo/registry.json."""

from __future__ import annotations

import json
from pathlib import Path


class Registry:
    """In-memory representation of the skill registry."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        with open(self.path) as f:
            data = json.load(f)
        self.skills: list[dict] = data.get("skills", [])

    def get(self, name: str) -> dict | None:
        """Get a skill by exact name."""
        for skill in self.skills:
            if skill["name"] == name:
                return skill
        return None

    def list_all(self) -> list[dict]:
        """List all skills, sorted alphabetically by name."""
        return sorted(self.skills, key=lambda s: s["name"])

    def list_by_category(self, category: str) -> list[dict]:
        """List skills matching a category."""
        return sorted(
            [s for s in self.skills if s.get("category") == category],
            key=lambda s: s["name"],
        )

    def search(self, query: str) -> list[dict]:
        """Search skills by matching query against name, description, and tags."""
        query_lower = query.lower()
        terms = query_lower.split()
        results = []
        for skill in self.skills:
            searchable = " ".join([
                skill.get("name", ""),
                skill.get("description", ""),
                skill.get("category", ""),
                " ".join(skill.get("tags", [])),
            ]).lower()
            if all(term in searchable for term in terms):
                results.append(skill)
        return sorted(results, key=lambda s: s["name"])

    def add(self, skill: dict) -> None:
        """Add a skill to the registry. Raises ValueError if name exists."""
        name = skill.get("name", "")
        if self.get(name) is not None:
            raise ValueError(f"Skill '{name}' already exists in registry")
        self.skills.append(skill)

    def remove(self, name: str) -> None:
        """Remove a skill by name. Raises ValueError if not found."""
        for i, skill in enumerate(self.skills):
            if skill["name"] == name:
                self.skills.pop(i)
                return
        raise ValueError(f"Skill '{name}' not found in registry")

    def save(self) -> None:
        """Write registry back to disk."""
        data = {"skills": sorted(self.skills, key=lambda s: s["name"])}
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_registry.py -v`
Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add cli_me/registry.py tests/test_registry.py
git commit -m "feat: add skill registry module with search and CRUD"
```

---

## Task 3: Installer Module

**Files:**
- Create: `cli_me/installer.py`
- Create: `tests/test_installer.py`

- [ ] **Step 1: Write failing tests for install and uninstall**

Create `tests/test_installer.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_installer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cli_me.installer'`

- [ ] **Step 3: Implement installer module**

Create `cli_me/installer.py`:

```python
"""Skill installer: copy skills to project or global Claude directories."""

from __future__ import annotations

import shutil
from pathlib import Path


class Installer:
    """Copies skill folders from skill-repo to target locations."""

    def __init__(self, skill_repo: Path | str) -> None:
        self.skill_repo = Path(skill_repo)

    def _resolve_dest(
        self,
        name: str,
        project_path: Path | str | None = None,
        global_dir: Path | str | None = None,
        global_install: bool = False,
    ) -> Path:
        if global_install:
            base = Path(global_dir) if global_dir else Path.home() / ".claude"
            return base / "skills" / name
        if project_path is None:
            raise ValueError("project_path required for project install")
        return Path(project_path) / ".claude" / "skills" / name

    def install(
        self,
        name: str,
        project_path: Path | str | None = None,
        global_dir: Path | str | None = None,
        global_install: bool = False,
        force: bool = False,
    ) -> Path:
        """Copy a skill from skill-repo to the target directory.

        Returns the destination path.
        """
        source = self.skill_repo / name
        if not source.is_dir():
            raise ValueError(
                f"Skill '{name}' not found in skill-repo at {self.skill_repo}"
            )

        dest = self._resolve_dest(name, project_path, global_dir, global_install)

        if dest.exists() and not force:
            raise FileExistsError(
                f"Skill '{name}' already installed at {dest}. Use --force to overwrite."
            )

        if dest.exists():
            shutil.rmtree(dest)

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)
        return dest

    def uninstall(
        self,
        name: str,
        project_path: Path | str | None = None,
        global_dir: Path | str | None = None,
        global_install: bool = False,
    ) -> None:
        """Remove an installed skill."""
        dest = self._resolve_dest(name, project_path, global_dir, global_install)
        if not dest.exists():
            raise FileNotFoundError(
                f"Skill '{name}' not installed at {dest}"
            )
        shutil.rmtree(dest)

    def list_installed(
        self,
        project_path: Path | str | None = None,
        global_dir: Path | str | None = None,
        global_install: bool = False,
    ) -> list[str]:
        """List installed skill names."""
        if global_install:
            base = Path(global_dir) if global_dir else Path.home() / ".claude"
            skills_dir = base / "skills"
        else:
            if project_path is None:
                return []
            skills_dir = Path(project_path) / ".claude" / "skills"

        if not skills_dir.exists():
            return []

        return sorted(
            d.name
            for d in skills_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_installer.py -v`
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add cli_me/installer.py tests/test_installer.py
git commit -m "feat: add skill installer with copy, uninstall, and list"
```

---

## Task 4: CLI App

**Files:**
- Create: `cli_me/main.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for CLI commands**

Create `tests/test_cli.py`:

```python
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
    assert "gimp" not in result.output


def test_search(fake_repo):
    result = runner.invoke(app, ["search", "pod"])
    assert result.exit_code == 0
    assert "gimp" in result.output


def test_search_no_results(fake_repo):
    result = runner.invoke(app, ["search", "nonexistent"])
    assert result.exit_code == 0
    assert "No skills found" in result.output


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cli_me.main'`

- [ ] **Step 3: Implement CLI app**

Create `cli_me/main.py`:

```python
"""cli-me: Agent-native skills for GUI software."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from cli_me.installer import Installer
from cli_me.registry import Registry

app = typer.Typer(
    name="clime",
    help="Agent-native skills for GUI software — build, install, and evolve Claude Code skills.",
    no_args_is_help=True,
)


def _find_skill_repo() -> Path:
    """Locate the skill-repo directory."""
    env = os.environ.get("CLIME_SKILL_REPO")
    if env:
        return Path(env)
    # Default: skill-repo/ relative to this package's repo root
    return Path(__file__).resolve().parent.parent / "skill-repo"


def _get_registry() -> Registry:
    repo = _find_skill_repo()
    return Registry(repo / "registry.json")


def _get_installer() -> Installer:
    return Installer(_find_skill_repo())


@app.command()
def list(
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
) -> None:
    """List available skills in the skill-repo."""
    reg = _get_registry()
    if category:
        skills = reg.list_by_category(category)
    else:
        skills = reg.list_all()

    if not skills:
        typer.echo("No skills found.")
        return

    for skill in skills:
        tags = ", ".join(skill.get("tags", []))
        typer.echo(f"  {skill['name']:<20} {skill.get('category', ''):<15} {tags}")


@app.command()
def search(query: str = typer.Argument(..., help="Search query")) -> None:
    """Search skills by name, description, or tags."""
    reg = _get_registry()
    results = reg.search(query)
    if not results:
        typer.echo("No skills found matching query.")
        return
    for skill in results:
        typer.echo(f"  {skill['name']:<20} {skill.get('description', '')}")


@app.command()
def info(name: str = typer.Argument(..., help="Skill name")) -> None:
    """Show detailed information about a skill."""
    reg = _get_registry()
    skill = reg.get(name)
    if skill is None:
        typer.echo(f"Skill '{name}' not found.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Name:         {skill['name']}")
    typer.echo(f"Description:  {skill.get('description', '')}")
    typer.echo(f"Category:     {skill.get('category', '')}")
    typer.echo(f"Tags:         {', '.join(skill.get('tags', []))}")
    typer.echo(f"Version:      {skill.get('version', '')}")
    typer.echo(f"Software:     {skill.get('software_url', '')}")
    typer.echo(f"Source:       {skill.get('source_repo', '')}")
    deps = skill.get("dependencies", [])
    if deps:
        typer.echo(f"Dependencies: {', '.join(deps)}")


@app.command()
def install(
    name: str = typer.Argument(..., help="Skill name to install"),
    project: str = typer.Option(None, "--project", "-p", help="Project directory"),
    global_: bool = typer.Option(False, "--global", "-g", help="Install globally"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing"),
) -> None:
    """Install a skill to a project or globally."""
    if not project and not global_:
        typer.echo("Specify --project <path> or --global.", err=True)
        raise typer.Exit(code=1)

    installer = _get_installer()
    try:
        dest = installer.install(
            name,
            project_path=project,
            global_install=global_,
            force=force,
        )
        typer.echo(f"Installed '{name}' to {dest}")
    except (ValueError, FileExistsError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)


@app.command()
def uninstall(
    name: str = typer.Argument(..., help="Skill name to uninstall"),
    project: str = typer.Option(None, "--project", "-p", help="Project directory"),
    global_: bool = typer.Option(False, "--global", "-g", help="Uninstall globally"),
) -> None:
    """Uninstall a skill from a project or globally."""
    if not project and not global_:
        typer.echo("Specify --project <path> or --global.", err=True)
        raise typer.Exit(code=1)

    installer = _get_installer()
    try:
        installer.uninstall(name, project_path=project, global_install=global_)
        typer.echo(f"Uninstalled '{name}'.")
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)


def main() -> None:
    app()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all 11 tests PASS

- [ ] **Step 5: Verify the entry point works**

Run: `uv run clime --help`
Expected: shows help with list, search, info, install, uninstall commands

Run: `uv run cli-me --help`
Expected: same output (alias works)

- [ ] **Step 6: Commit**

```bash
git add cli_me/main.py tests/test_cli.py
git commit -m "feat: add clime CLI with list, search, info, install, uninstall"
```

---

## Task 5: Meta-Skill — SKILL.md

**Files:**
- Create: `.claude/skills/cli-me-meta/SKILL.md`

- [ ] **Step 1: Write the meta-skill**

Create `.claude/skills/cli-me-meta/SKILL.md`:

```markdown
---
name: cli-me-meta
description: Build high-quality Claude Code skills that wrap GUI software. Use when
  asked to "build a skill for", "wrap", "create a CLI for", or "make a skill" for
  any desktop application. Drives a multi-phase process of source code research, web
  research, wiki creation, CLI scaffolding, and testing.
---

# cli-me Meta-Skill: Build Agent-Native Skills for GUI Software

You are building a cli-me skill — a Claude Code skill that wraps a GUI application
with a Typer CLI so agents can operate it headlessly. Every skill you build must
follow the principles and phases below.

## Principles

1. **Call the real software, don't reimplement it.** Your Typer CLI generates valid
   inputs and invokes the real application via subprocess or REST API. If the software
   isn't installed, fail loudly with install instructions.
2. **Research the source, don't guess.** Clone the software's repo and read the actual
   code to find the API surface, scripting interfaces, and headless modes.
3. **Concept-to-command mapping.** Wiki pages translate domain knowledge into executable
   CLI commands. An agent using the skill should never see "click this then that."
4. **Self-evolving knowledge.** Every generated skill instructs agents to write back
   what they learned to the wiki after each use.
5. **Attribution always.** Every wiki page links back to source URLs.

## Phase 1: Research

### 1a. Clone the source

Clone the target software's repository to `tmp/source-analysis/<name>/`:

```bash
git clone <repo-url> tmp/source-analysis/<name>
```

If the repo is very large, use `--depth 1` for a shallow clone.

### 1b. Analyze the codebase

Read the cloned source to answer these questions. Write findings to wiki pages
as you go (don't wait until the end):

- **API surface** → `references/source-analysis/api-surface.md`
  - What scripting interfaces exist? (Python bindings, Script-Fu, REST API, CLI flags)
  - What are the main entry points for headless/batch operation?
  - What functions correspond to common GUI actions?

- **CLI interface** → `references/source-analysis/cli-interface.md`
  - What command-line flags does the software support?
  - What headless/batch modes are available?
  - How do you invoke it without a display?

- **Internal architecture** → `references/source-analysis/internal-architecture.md`
  - How is the software structured? (plugins, modules, node graph, etc.)
  - Where does the core logic live vs. the GUI layer?

- **Key functions** → `references/source-analysis/key-functions.md`
  - Document important functions with file paths and line numbers
  - Focus on functions the Typer CLI will need to invoke

- **Version** → `references/source-analysis/analyzed-version.md`
  - Record the git tag, commit hash, and date analyzed
  - Note the version string from the software's own metadata

### 1c. Research the web

Search for:
- Official documentation for headless/scripting usage
- Tutorials and best practices for batch processing
- Common workflows and use cases
- Known issues and workarounds
- Community scripts and automation examples

Write findings as technique pages in `references/techniques/`. Every page must
include source URLs.

### 1d. Initialize the wiki

Create the wiki operational files:

- `references/index.md` — table of contents linking to all pages created above
- `references/log.md` — first entry: "YYYY-MM-DD: Initial research completed.
  Analyzed <software> <version>. Created source analysis and technique pages."
- `references/gotchas.md` — any issues or warnings discovered during research

## Phase 2: Scaffold

Create the skill folder structure:

```
skill-repo/<name>/
├── SKILL.md
├── scripts/
│   ├── pyproject.toml        # Standalone — declares Typer dep so uv run works
│   └── <name>_cli.py
└── references/
    ├── index.md
    ├── log.md
    ├── gotchas.md
    ├── source-analysis/
    │   ├── analyzed-version.md
    │   ├── api-surface.md
    │   ├── cli-interface.md
    │   ├── internal-architecture.md
    │   ├── key-functions.md
    │   └── changelog.md
    └── techniques/
        └── (pages from Phase 1)
```

Generate the SKILL.md using the template at `references/skill-template.md`.

Add an entry to `skill-repo/registry.json` using the Registry class or by
appending to the JSON directly:

```json
{
  "name": "<name>",
  "description": "<one-line description>",
  "category": "<category>",
  "tags": ["<tag1>", "<tag2>"],
  "version": "0.1.0",
  "software_url": "<software homepage>",
  "source_repo": "<git clone url>",
  "dependencies": []
}
```

## Phase 3: Implement

Create `scripts/pyproject.toml` so the CLI is self-contained and `uv run` works
without the cli-me repo:

```toml
[project]
name = "{{name}}-cli"
version = "0.1.0"
description = "Agent-native CLI for {{Software Name}}"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
]

[project.scripts]
{{name}}-cli = "{{name}}_cli:app"
```

Write the Typer CLI at `scripts/<name>_cli.py`. Follow the template at
`references/typer-cli-template.md`.

Every CLI must include:

```python
import subprocess
import shutil
import typer

app = typer.Typer(help="<name> CLI — agent-native interface for <Software>")


def detect_version() -> tuple[int, ...]:
    """Detect installed software version."""
    path = shutil.which("<executable>")
    if path is None:
        typer.echo(
            "ERROR: <Software> not found. Install with: <install instructions>",
            err=True,
        )
        raise typer.Exit(code=1)
    result = subprocess.run(
        [path, "--version"], capture_output=True, text=True
    )
    # Parse version from output
    ...


def find_executable() -> str:
    """Find the software executable or exit with install instructions."""
    path = shutil.which("<executable>")
    if path is None:
        typer.echo(
            "ERROR: <Software> not found. Install with: <install instructions>",
            err=True,
        )
        raise typer.Exit(code=1)
    return path
```

Commands should map to the workflows and techniques documented in the wiki.
Use version-aware branching where needed:

```python
version = detect_version()
if version >= (3, 0):
    # new approach
else:
    # legacy approach
```

## Phase 4: Test

1. Run each CLI command against the real installed software
2. Verify outputs exist and are correct (file size > 0, correct format, etc.)
3. Test `--help` on all commands
4. Document test results in `references/log.md`

## Phase 5: Write-back Instruction

Append the standard write-back section to the generated SKILL.md. Read the exact
text from `references/write-back-instructions.md` and append it verbatim.

## After You (the Meta-Skill) Complete a Build

Update your own wiki at `references/meta-wiki/`:
1. Append to `references/meta-wiki/log.md` what you learned about building this skill
2. If you discovered a better research strategy, pattern, or pitfall, update the
   relevant reference file
3. Update `references/meta-wiki/index.md` if you added new pages
```

- [ ] **Step 2: Verify the skill is discoverable**

Run: `ls .claude/skills/cli-me-meta/SKILL.md`
Expected: file exists

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/cli-me-meta/SKILL.md
git commit -m "feat: add cli-me-meta skill — the skill builder"
```

---

## Task 6: Meta-Skill — Reference Templates

**Files:**
- Create: `.claude/skills/cli-me-meta/references/skill-template.md`
- Create: `.claude/skills/cli-me-meta/references/wiki-template.md`
- Create: `.claude/skills/cli-me-meta/references/technique-page-template.md`
- Create: `.claude/skills/cli-me-meta/references/typer-cli-template.md`
- Create: `.claude/skills/cli-me-meta/references/write-back-instructions.md`
- Create: `.claude/skills/cli-me-meta/references/meta-wiki/index.md`
- Create: `.claude/skills/cli-me-meta/references/meta-wiki/log.md`

- [ ] **Step 1: Create the SKILL.md template**

Create `.claude/skills/cli-me-meta/references/skill-template.md`:

```markdown
# Skill Template

Use this template when generating a new skill's SKILL.md. Replace all
`{{placeholders}}` with actual values.

---

\```markdown
---
name: {{name}}
description: {{description — what it does + when to use it. Include trigger
  phrases like "edit images", "remove background", "batch process". Under 1024
  characters. No XML angle brackets.}}
---

# {{Software Name}} — cli-me skill

CLI-powered interface for {{Software Name}}. This skill wraps the real
{{Software}} executable — it does not reimplement functionality in Python.

## Prerequisites

- {{Software}} must be installed: `{{install command}}`
- Python 3.12+

## CLI Commands

Run commands via:
\```bash
uv run scripts/{{name}}_cli.py <command> [options]
\```

### Available Commands

{{List each command group and command with a one-line description}}

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how something works under the hood, check
`references/source-analysis/`.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Append a timestamped entry to `references/log.md` with what you did and
   what you learned
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
\```
```

- [ ] **Step 2: Create the wiki initialization template**

Create `.claude/skills/cli-me-meta/references/wiki-template.md`:

```markdown
# Wiki Initialization Template

Use this when scaffolding a new skill's references/ directory.

## Files to create

### references/index.md

\```markdown
# {{Software Name}} Knowledge Base

## Source Analysis
- [Analyzed Version](source-analysis/analyzed-version.md) — version and analysis metadata
- [API Surface](source-analysis/api-surface.md) — scripting interfaces and bindings
- [CLI Interface](source-analysis/cli-interface.md) — headless modes and flags
- [Internal Architecture](source-analysis/internal-architecture.md) — how the software is structured
- [Key Functions](source-analysis/key-functions.md) — important functions for CLI wrapping
- [Changelog](source-analysis/changelog.md) — version deltas

## Techniques
{{Add links as technique pages are created}}

## Operational
- [Gotchas](gotchas.md) — known issues and workarounds
- [Learning Log](log.md) — chronological record of learnings
\```

### references/log.md

\```markdown
# Learning Log

Append-only chronological record. Newest entries at the bottom.

---

**{{YYYY-MM-DD}}** — Initial research completed. Analyzed {{Software}} {{version}}.
Created source analysis and technique pages from codebase review and web research.
\```

### references/gotchas.md

\```markdown
# Gotchas

Known issues, failure modes, and workarounds discovered through research and usage.

{{Add entries as they are discovered}}
\```

### references/source-analysis/analyzed-version.md

\```markdown
# Analyzed Version

**Current:** {{Software}} {{version}} (commit {{hash}}, analyzed {{YYYY-MM-DD}})

## Analysis History

| Date | Version | Commit | Notes |
|------|---------|--------|-------|
| {{YYYY-MM-DD}} | {{version}} | {{hash}} | Initial analysis |
\```

### references/source-analysis/changelog.md

\```markdown
# Changelog

Version deltas: what changed in the software's API, CLI, and internals.
Updated when re-analyzing a new version.

{{No entries yet — will be populated on version updates}}
\```
```

- [ ] **Step 3: Create the technique page template**

Create `.claude/skills/cli-me-meta/references/technique-page-template.md`:

```markdown
# Technique Page Template

Every technique page in references/techniques/ must follow this structure.
The three layers (domain knowledge, executable knowledge, provenance) are
mandatory — don't skip any.

---

\```markdown
# {{Technique Name}}

## When to Use
{{Describe the scenarios where this technique applies.
Be specific — "product photos for POD" not "when editing images".}}

## Technique
{{Explain the concept. What is this, how does it work, what parameters
matter, what are common mistakes. This is the domain knowledge layer.}}

## CLI Commands
\```bash
# {{Description of what this command does}}
uv run scripts/{{name}}_cli.py {{command}} {{flags}}
\```

## Under the Hood
{{What does the CLI command actually do? Which software functions does it
call? Link to source-analysis/key-functions.md for details.}}

## Sources
- [{{Source title}}]({{url}})
- Analyzed from: {{Software}} {{version}} (see analyzed-version.md)

## Learned from Usage
{{This section grows over time as agents use the skill.
Format: YYYY-MM-DD: What happened and what was learned.}}
\```
```

- [ ] **Step 4: Create the Typer CLI template**

Create `.claude/skills/cli-me-meta/references/typer-cli-template.md`:

```markdown
# Typer CLI Template

Use this as the starting point for every skill's scripts/ directory.
Each skill's scripts/ is self-contained — it has its own pyproject.toml
so `uv run` works without the cli-me repo.

## scripts/pyproject.toml

\```toml
[project]
name = "{{name}}-cli"
version = "0.1.0"
description = "Agent-native CLI for {{Software Name}}"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
]

[project.scripts]
{{name}}-cli = "{{name}}_cli:app"
\```

## scripts/{{name}}_cli.py

\```python
"""{{name}}_cli: Agent-native CLI for {{Software Name}}.

Calls the real {{Software}} executable — does not reimplement functionality.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="{{name}}-cli",
    help="Agent-native CLI for {{Software Name}}.",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

def find_executable() -> str:
    """Locate the {{Software}} executable or exit with install instructions."""
    path = shutil.which("{{executable}}")
    if path is None:
        typer.echo(
            "ERROR: {{Software}} not found in PATH.\n"
            "Install with: {{install_command}}",
            err=True,
        )
        raise typer.Exit(code=1)
    return path


def detect_version() -> tuple[int, ...]:
    """Detect installed {{Software}} version."""
    exe = find_executable()
    result = subprocess.run(
        [exe, "{{version_flag}}"],
        capture_output=True,
        text=True,
    )
    # Parse version — adapt this to the software's output format
    # Example: "GIMP 2.10.38" → (2, 10, 38)
    version_str = result.stdout.strip().split()[-1]
    return tuple(int(x) for x in version_str.split("."))


def run_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a {{Software}} command and return the result."""
    exe = find_executable()
    return subprocess.run(
        [exe] + args,
        capture_output=True,
        text=True,
        check=check,
    )


# ---------------------------------------------------------------------------
# Commands — add command groups matching the software's workflow domains
# ---------------------------------------------------------------------------

@app.command()
def version() -> None:
    """Show the installed {{Software}} version."""
    v = detect_version()
    typer.echo(f"{{Software}} {'.'.join(str(x) for x in v)}")


# Add more commands here based on the research phase findings.
# Group related commands using typer.Typer() sub-apps if needed.

if __name__ == "__main__":
    app()
\```
```

- [ ] **Step 5: Create the write-back instructions**

Create `.claude/skills/cli-me-meta/references/write-back-instructions.md`:

```markdown
# Write-Back Instructions

Append this section verbatim to every generated SKILL.md. This is what
makes skills self-evolving.

---

\```markdown
## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Append a timestamped entry to `references/log.md` with what you did and
   what you learned
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
\```
```

- [ ] **Step 6: Create the meta-skill's own wiki**

Create `.claude/skills/cli-me-meta/references/meta-wiki/index.md`:

```markdown
# cli-me Meta-Skill Knowledge Base

This wiki captures what the meta-skill has learned about building skills.
It self-improves as more skills are built.

## Pages

- [Learning Log](log.md) — chronological record of builds and lessons learned

## Patterns Discovered

{{Will be populated as skills are built}}

## Pitfalls

{{Will be populated as problems are encountered}}
```

Create `.claude/skills/cli-me-meta/references/meta-wiki/log.md`:

```markdown
# Meta-Skill Learning Log

Append-only. Newest entries at the bottom.

---

{{No entries yet — will be populated when the first skill is built}}
```

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/cli-me-meta/references/
git commit -m "feat: add meta-skill reference templates and wiki"
```

---

## Task 7: Integration Test — Full Workflow

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write an integration test that exercises the full install flow**

Create `tests/test_integration.py`:

```python
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

    # Verify SKILL.md content
    skill_content = (installed / "SKILL.md").read_text()
    assert "name: gimp" in skill_content
    assert "After Completing Your Task" in skill_content

    # Info command works
    result = runner.invoke(app, ["info", "gimp"])
    assert result.exit_code == 0
    assert "image-editing" in result.output

    # Search finds it
    result = runner.invoke(app, ["search", "pod"])
    assert result.exit_code == 0
    assert "gimp" in result.output

    # Uninstall
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

    # Verify it shows up
    result = runner.invoke(app, ["list"])
    assert "blender" in result.output
    assert "gimp" in result.output

    # Install it
    project = tmp_path / "project2"
    project.mkdir()
    result = runner.invoke(app, ["install", "blender", "--project", str(project)])
    assert result.exit_code == 0
    assert (project / ".claude" / "skills" / "blender" / "SKILL.md").exists()
```

- [ ] **Step 2: Run the integration tests**

Run: `uv run pytest tests/test_integration.py -v`
Expected: all tests PASS

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest tests/ -v`
Expected: all tests PASS across all test files

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full install workflow"
```

---

## Task 8: Final Cleanup

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the README**

Write `README.md`:

```markdown
# cli-me

Agent-native skills for GUI software. Build, install, and evolve Claude Code
skills that wrap desktop applications with Typer CLIs.

## What is this?

cli-me is a framework for creating Claude Code skills that let AI agents operate
GUI software headlessly. Each skill includes:

- **SKILL.md** — teaches Claude when and how to use the software
- **scripts/** — a Typer CLI that calls the real software (never reimplements it)
- **references/** — a self-evolving wiki that grows smarter with every use

## Quick Start

```bash
# List available skills
uv run clime list

# Install a skill to your project
uv run clime install gimp --project .

# Install globally
uv run clime install gimp --global

# Search for skills
uv run clime search "image editing"

# Get skill details
uv run clime info gimp
```

## Building Skills

The meta-skill at `.claude/skills/cli-me-meta/` guides Claude through building
new skills. In a Claude Code session within this repo:

> "Build me a cli-me skill for GIMP"

The meta-skill drives a multi-phase process: research the source code, search
for best practices, build the wiki, scaffold the CLI, test it, and publish it
to the skill-repo.

## Project Structure

```
cli-me/
├── .claude/skills/cli-me-meta/  # The skill builder
├── skill-repo/                  # Published skills
├── cli_me/                      # Installer CLI (clime)
└── tests/
```

## Design

See [docs/superpowers/specs/2026-04-14-cli-me-design.md](docs/superpowers/specs/2026-04-14-cli-me-design.md)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

- [ ] **Step 3: Run final verification**

Run: `uv run pytest tests/ -v`
Expected: all tests PASS

Run: `uv run clime --help`
Expected: shows help

Run: `uv run clime list`
Expected: shows empty list (no skills in repo yet)

---

## Summary

| Task | What it builds | Tests |
|------|----------------|-------|
| 1 | Repo scaffolding (pyproject.toml, .gitignore, registry, package) | `uv sync` verification |
| 2 | Registry module (load, search, CRUD, save) | 12 unit tests |
| 3 | Installer module (copy, uninstall, list installed) | 8 unit tests |
| 4 | CLI app (list, search, info, install, uninstall) | 11 CLI tests |
| 5 | Meta-skill SKILL.md | file existence check |
| 6 | Meta-skill reference templates and wiki | file existence checks |
| 7 | Integration test (full workflow) | 2 integration tests |
| 8 | README and final verification | full suite run |

Total: ~33 tests across 4 test files.
