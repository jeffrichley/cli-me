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
