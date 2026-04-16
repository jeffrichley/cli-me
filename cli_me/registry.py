"""Skill registry: load, search, and manage skill-repo/registry.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from filelock import FileLock

from cli_me.filelock import locked_write


class Registry:
    """In-memory representation of the skill registry."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        with open(self.path) as f:
            data = json.load(f)
        self.skills: list[dict] = data.get("skills", [])

    @classmethod
    def locked_modify(
        cls,
        path: Path | str,
        modifier: Callable[["Registry"], None],
        timeout: float = 30.0,
    ) -> "Registry":
        """Read-modify-write the registry under a single lock.

        This prevents TOCTOU races: the lock is held for the entire
        read → modify → write cycle, so concurrent agents can't lose
        each other's updates.

        *modifier* receives a Registry instance and mutates it in place.
        The modified registry is saved and returned.
        """
        path = Path(path)
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock = FileLock(lock_path, timeout=timeout)

        with lock:
            reg = cls.__new__(cls)
            reg.path = path
            with open(path) as f:
                data = json.load(f)
            reg.skills = data.get("skills", [])

            modifier(reg)

            out = {"skills": sorted(reg.skills, key=lambda s: s["name"])}
            with open(path, "w") as f:
                json.dump(out, f, indent=2)
                f.write("\n")

        return reg

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
        """Write registry back to disk with file locking and atomic write."""
        data = {"skills": sorted(self.skills, key=lambda s: s["name"])}

        def writer(path: Path) -> None:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")

        locked_write(self.path, writer)
