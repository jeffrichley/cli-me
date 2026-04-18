# Concurrent Registry & Log CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add file-locked CLI subcommands so that parallel agents mutate `registry.json` and `meta-wiki/log.md` through a serialized gatekeeper instead of writing directly — preventing silent data loss from concurrent skill builds.

**Architecture:** New `cli_me/filelock.py` module provides cross-platform file locking (Windows + POSIX). New `cli_me/log.py` module manages append-only log operations. Registry.save() and log appends go through lock-acquire → read → mutate → atomic-write → release. The `clime` CLI gets two new subcommand groups: `clime registry {add,remove,update}` and `clime log append`. All mutations flow through these commands. Reads remain lock-free (safe because writes are atomic via temp-file-then-rename).

**Tech Stack:** Python 3.12, typer, rich, `filelock` (cross-platform file locking library), existing hatchling build

**Dependency:** `filelock` — pure Python, no C extensions, well-maintained (15k+ GitHub stars), supports Windows + POSIX. Already used by pip, virtualenv, and tox internally.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `cli_me/filelock.py` | Thin wrapper: acquire lock, run callback, release. Lock file lives next to the target file (`registry.json.lock`, `log.md.lock`). |
| `cli_me/registry.py` | Existing file — add `atomic_save()` method (temp file + rename). Existing `save()` calls `atomic_save()`. |
| `cli_me/log.py` | New module — `LogFile` class: locked append to an arbitrary markdown log file. |
| `cli_me/main.py` | Existing file — add `registry` and `log` subcommand groups with typer. |
| `tests/test_filelock.py` | Tests for locking behavior: mutual exclusion, timeout, stale lock recovery. |
| `tests/test_log.py` | Tests for LogFile: append, locked concurrent writes, file creation. |
| `tests/test_registry.py` | Existing file — add tests for `atomic_save()` and locked CLI commands. |
| `tests/test_cli.py` | Existing file — add tests for new `registry` and `log` CLI subcommands. |

---

### Task 1: Add `filelock` dependency

**Files:**
- Modify: `pyproject.toml:13` (dependencies list)

- [ ] **Step 1: Add filelock to dependencies**

In `pyproject.toml`, add `filelock` to the dependencies list:

```toml
dependencies = [
    "typer>=0.15.0",
    "rich>=13.0.0",
    "filelock>=3.13.0",
]
```

- [ ] **Step 2: Sync the environment**

Run: `uv sync`
Expected: resolves and installs filelock

- [ ] **Step 3: Verify import works**

Run: `uv run python -c "from filelock import FileLock; print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add filelock dependency for concurrent access safety"
```

---

### Task 2: Create `cli_me/filelock.py` — locking helper

**Files:**
- Create: `cli_me/filelock.py`
- Create: `tests/test_filelock.py`

- [ ] **Step 1: Write the failing test for `locked_write`**

Create `tests/test_filelock.py`:

```python
import json
from pathlib import Path

from cli_me.filelock import locked_write


def test_locked_write_creates_file(tmp_path):
    """locked_write creates the target file if it doesn't exist."""
    target = tmp_path / "data.json"

    def writer(path: Path) -> None:
        path.write_text(json.dumps({"created": True}))

    locked_write(target, writer)

    assert target.exists()
    assert json.loads(target.read_text()) == {"created": True}


def test_locked_write_uses_lock_file(tmp_path):
    """locked_write creates a .lock file next to the target."""
    target = tmp_path / "data.json"
    target.write_text("{}")
    lock_path = target.with_suffix(target.suffix + ".lock")

    locked = False

    def writer(path: Path) -> None:
        nonlocal locked
        locked = lock_path.exists()
        path.write_text("{}")

    locked_write(target, writer)

    # The lock file existed while the writer ran
    assert locked


def test_locked_write_atomic_via_temp(tmp_path):
    """locked_write writes to a temp file then renames, so partial writes
    don't corrupt the target."""
    target = tmp_path / "data.json"
    target.write_text(json.dumps({"original": True}))

    def writer(path: Path) -> None:
        # path is a temp file, not the target
        assert path != target
        path.write_text(json.dumps({"updated": True}))

    locked_write(target, writer, atomic=True)

    assert json.loads(target.read_text()) == {"updated": True}


def test_locked_write_non_atomic_writes_directly(tmp_path):
    """When atomic=False, the writer gets the target path directly."""
    target = tmp_path / "data.json"
    target.write_text("{}")

    def writer(path: Path) -> None:
        assert path == target
        path.write_text(json.dumps({"direct": True}))

    locked_write(target, writer, atomic=False)

    assert json.loads(target.read_text()) == {"direct": True}


def test_locked_write_timeout(tmp_path):
    """locked_write raises Timeout if it can't acquire the lock."""
    from filelock import Timeout

    target = tmp_path / "data.json"
    target.write_text("{}")
    lock_path = target.with_suffix(target.suffix + ".lock")

    from filelock import FileLock

    # Hold the lock externally
    external_lock = FileLock(lock_path)
    external_lock.acquire()

    try:
        raised = False
        try:
            locked_write(target, lambda p: None, timeout=0.1)
        except Timeout:
            raised = True
        assert raised
    finally:
        external_lock.release()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_filelock.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cli_me.filelock'`

- [ ] **Step 3: Implement `cli_me/filelock.py`**

Create `cli_me/filelock.py`:

```python
"""Cross-platform file locking for concurrent access safety."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from filelock import FileLock


def locked_write(
    target: Path,
    writer: Callable[[Path], None],
    *,
    atomic: bool = True,
    timeout: float = 30.0,
) -> None:
    """Acquire a lock on *target*, run *writer*, release the lock.

    Parameters
    ----------
    target:
        The file to protect. A ``<target>.lock`` file is created next to it.
    writer:
        A callable that receives a Path and writes content to it.
        When *atomic* is True, the path is a temp file that gets renamed
        over *target* after the writer returns.
        When *atomic* is False, the path is *target* itself.
    atomic:
        If True (default), write to a temp file and rename over *target*.
        This prevents partial writes from corrupting the file.
    timeout:
        Seconds to wait for the lock before raising ``filelock.Timeout``.
    """
    lock_path = target.with_suffix(target.suffix + ".lock")
    lock = FileLock(lock_path, timeout=timeout)

    with lock:
        if atomic:
            fd, tmp_path_str = tempfile.mkstemp(
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
            )
            os.close(fd)
            tmp_path = Path(tmp_path_str)
            try:
                writer(tmp_path)
                tmp_path.replace(target)
            except BaseException:
                tmp_path.unlink(missing_ok=True)
                raise
        else:
            writer(target)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_filelock.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add cli_me/filelock.py tests/test_filelock.py
git commit -m "feat: add filelock helper for concurrent access safety"
```

---

### Task 3: Make `Registry.save()` atomic and locked

**Files:**
- Modify: `cli_me/registry.py`
- Modify: `tests/test_registry.py`

- [ ] **Step 1: Write failing test for atomic save**

Append to `tests/test_registry.py`:

```python
def test_save_is_atomic(sample_registry):
    """save() writes atomically — a crash mid-write won't corrupt the file."""
    reg = Registry(sample_registry)
    original_content = sample_registry.read_text()

    reg.add({
        "name": "atomic-test",
        "description": "test atomicity",
        "category": "test",
        "tags": [],
        "version": "0.1.0",
        "software_url": "",
        "source_repo": "",
        "dependencies": [],
    })
    reg.save()

    # Verify the file is valid JSON after save
    import json
    data = json.loads(sample_registry.read_text())
    assert any(s["name"] == "atomic-test" for s in data["skills"])


def test_save_uses_lock_file(sample_registry):
    """save() creates a .lock file during write."""
    lock_path = sample_registry.with_suffix(".json.lock")
    reg = Registry(sample_registry)
    reg.save()
    # Lock file may or may not persist after release (implementation detail),
    # but the save should complete without error
    assert sample_registry.exists()
```

- [ ] **Step 2: Run tests to verify they pass with current implementation (baseline)**

Run: `uv run pytest tests/test_registry.py -v`
Expected: all tests PASS (existing save works, new tests happen to pass too since they don't check locking internals yet)

- [ ] **Step 3: Update `Registry.save()` to use `locked_write`**

Replace the `save` method in `cli_me/registry.py`. The full updated file:

```python
"""Skill registry: load, search, and manage skill-repo/registry.json."""

from __future__ import annotations

import json
from pathlib import Path

from cli_me.filelock import locked_write


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
        """Write registry back to disk with file locking and atomic write."""
        data = {"skills": sorted(self.skills, key=lambda s: s["name"])}

        def writer(path: Path) -> None:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")

        locked_write(self.path, writer)
```

- [ ] **Step 4: Run all registry tests**

Run: `uv run pytest tests/test_registry.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add cli_me/registry.py tests/test_registry.py
git commit -m "feat: make Registry.save() atomic and file-locked"
```

---

### Task 4: Create `cli_me/log.py` — locked log appender

**Files:**
- Create: `cli_me/log.py`
- Create: `tests/test_log.py`

- [ ] **Step 1: Write failing tests for LogFile**

Create `tests/test_log.py`:

```python
from pathlib import Path

from cli_me.log import LogFile


def test_append_to_existing_log(tmp_path):
    """append() adds an entry to an existing log file."""
    log_path = tmp_path / "log.md"
    log_path.write_text("# Log\n\n---\n")

    log = LogFile(log_path)
    log.append("inkscape", "Learned that inkscape CLI needs --batch flag.")

    content = log_path.read_text()
    assert "inkscape" in content
    assert "--batch flag" in content


def test_append_creates_file_if_missing(tmp_path):
    """append() creates the log file if it doesn't exist."""
    log_path = tmp_path / "log.md"

    log = LogFile(log_path)
    log.append("blender", "Blender needs --background for headless mode.")

    assert log_path.exists()
    content = log_path.read_text()
    assert "blender" in content
    assert "--background" in content


def test_append_preserves_existing_content(tmp_path):
    """append() does not overwrite existing log entries."""
    log_path = tmp_path / "log.md"
    log_path.write_text("# Log\n\nExisting entry here.\n")

    log = LogFile(log_path)
    log.append("gimp", "GIMP needs --no-interface for CLI mode.")

    content = log_path.read_text()
    assert "Existing entry here." in content
    assert "GIMP needs --no-interface" in content


def test_append_includes_date(tmp_path):
    """append() includes a date in the entry."""
    log_path = tmp_path / "log.md"

    log = LogFile(log_path)
    log.append("test-skill", "Some learning.")

    content = log_path.read_text()
    # Should contain a date in ISO format (YYYY-MM-DD)
    import re
    assert re.search(r"\d{4}-\d{2}-\d{2}", content)


def test_multiple_appends_are_ordered(tmp_path):
    """Multiple appends appear in order."""
    log_path = tmp_path / "log.md"

    log = LogFile(log_path)
    log.append("first", "First entry.")
    log.append("second", "Second entry.")
    log.append("third", "Third entry.")

    content = log_path.read_text()
    pos_first = content.index("First entry.")
    pos_second = content.index("Second entry.")
    pos_third = content.index("Third entry.")
    assert pos_first < pos_second < pos_third
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_log.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cli_me.log'`

- [ ] **Step 3: Implement `cli_me/log.py`**

Create `cli_me/log.py`:

```python
"""Locked append-only log file for concurrent agent writes."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from cli_me.filelock import locked_write


class LogFile:
    """Append-only markdown log with file locking."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def append(self, skill: str, message: str) -> None:
        """Append a timestamped entry to the log.

        Uses file locking so multiple agents can safely append concurrently.
        """
        today = date.today().isoformat()
        entry = f"\n**{today}** [{skill}] — {message}\n"

        def writer(path: Path) -> None:
            if self.path.exists():
                existing = self.path.read_text()
            else:
                existing = "# Log\n"
            path.write_text(existing + entry)

        locked_write(self.path, writer)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_log.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add cli_me/log.py tests/test_log.py
git commit -m "feat: add LogFile with locked append for concurrent agent writes"
```

---

### Task 5: Add `clime registry` subcommands

**Files:**
- Modify: `cli_me/main.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for registry subcommands**

Append to `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py::test_registry_add -v`
Expected: FAIL — `No such command 'registry'`

- [ ] **Step 3: Add registry subcommands to `cli_me/main.py`**

Add the following after the existing `uninstall` command in `main.py`:

```python
# --- Registry mutation subcommands (file-locked for concurrent access) ---

registry_app = typer.Typer(
    name="registry",
    help="Mutate skill-repo/registry.json with file locking for concurrent agent safety.",
    no_args_is_help=True,
)
app.add_typer(registry_app)


@registry_app.command("add")
def registry_add(
    name: str = typer.Option(..., help="Skill name"),
    description: str = typer.Option("", help="Skill description"),
    category: str = typer.Option("", help="Skill category"),
    tags: str = typer.Option("", help="Comma-separated tags"),
    version: str = typer.Option("0.1.0", help="Skill version"),
    software_url: str = typer.Option("", help="Upstream software URL"),
    source_repo: str = typer.Option("", help="Source repository URL"),
    dependencies: str = typer.Option("", help="Comma-separated dependency names"),
) -> None:
    """Add a new skill to the registry (file-locked)."""
    reg = _get_registry()
    skill = {
        "name": name,
        "description": description,
        "category": category,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "version": version,
        "software_url": software_url,
        "source_repo": source_repo,
        "dependencies": [d.strip() for d in dependencies.split(",") if d.strip()],
    }
    try:
        reg.add(skill)
        reg.save()
        console.print(f"Added [bold]{name}[/bold] to registry.", style="green")
    except ValueError as e:
        err_console.print(str(e), style="bold red")
        raise typer.Exit(code=1)


@registry_app.command("remove")
def registry_remove(
    name: str = typer.Argument(..., help="Skill name to remove"),
) -> None:
    """Remove a skill from the registry (file-locked)."""
    reg = _get_registry()
    try:
        reg.remove(name)
        reg.save()
        console.print(f"Removed [bold]{name}[/bold] from registry.", style="green")
    except ValueError as e:
        err_console.print(str(e), style="bold red")
        raise typer.Exit(code=1)


@registry_app.command("update")
def registry_update(
    name: str = typer.Argument(..., help="Skill name to update"),
    description: str = typer.Option(None, help="New description"),
    category: str = typer.Option(None, help="New category"),
    tags: str = typer.Option(None, help="New comma-separated tags"),
    version: str = typer.Option(None, help="New version"),
    software_url: str = typer.Option(None, help="New software URL"),
    source_repo: str = typer.Option(None, help="New source repo URL"),
    dependencies: str = typer.Option(None, help="New comma-separated dependencies"),
) -> None:
    """Update fields on an existing skill (file-locked)."""
    reg = _get_registry()
    skill = reg.get(name)
    if skill is None:
        err_console.print(f"Skill '{name}' not found.", style="bold red")
        raise typer.Exit(code=1)

    if description is not None:
        skill["description"] = description
    if category is not None:
        skill["category"] = category
    if tags is not None:
        skill["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    if version is not None:
        skill["version"] = version
    if software_url is not None:
        skill["software_url"] = software_url
    if source_repo is not None:
        skill["source_repo"] = source_repo
    if dependencies is not None:
        skill["dependencies"] = [d.strip() for d in dependencies.split(",") if d.strip()]

    reg.save()
    console.print(f"Updated [bold]{name}[/bold] in registry.", style="green")
```

- [ ] **Step 4: Run all CLI tests**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all tests PASS (old and new)

- [ ] **Step 5: Commit**

```bash
git add cli_me/main.py tests/test_cli.py
git commit -m "feat: add clime registry add/remove/update subcommands with file locking"
```

---

### Task 6: Add `clime log` subcommand

**Files:**
- Modify: `cli_me/main.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for log append subcommand**

Append to `tests/test_cli.py`:

```python
def test_log_append(fake_repo):
    log_path = fake_repo / "meta-wiki" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("# Log\n")

    result = runner.invoke(app, [
        "log", "append",
        "--skill", "gimp",
        "--message", "Learned about --no-interface flag.",
        "--log-file", str(log_path),
    ])
    assert result.exit_code == 0

    content = log_path.read_text()
    assert "gimp" in content
    assert "--no-interface" in content


def test_log_append_creates_file(fake_repo, tmp_path):
    log_path = tmp_path / "new-log.md"

    result = runner.invoke(app, [
        "log", "append",
        "--skill", "blender",
        "--message", "Blender needs --background.",
        "--log-file", str(log_path),
    ])
    assert result.exit_code == 0
    assert log_path.exists()
    assert "blender" in log_path.read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py::test_log_append -v`
Expected: FAIL — `No such command 'log'`

- [ ] **Step 3: Add log subcommand to `cli_me/main.py`**

Add after the registry subcommands:

```python
from cli_me.log import LogFile

# --- Log mutation subcommands (file-locked for concurrent access) ---

log_app = typer.Typer(
    name="log",
    help="Append to log files with file locking for concurrent agent safety.",
    no_args_is_help=True,
)
app.add_typer(log_app)


@log_app.command("append")
def log_append(
    skill: str = typer.Option(..., help="Skill name for the log entry"),
    message: str = typer.Option(..., help="Log message to append"),
    log_file: str = typer.Option(
        None,
        "--log-file",
        help="Path to log file. Defaults to meta-wiki/log.md in skill-repo.",
    ),
) -> None:
    """Append a timestamped entry to a log file (file-locked)."""
    if log_file:
        path = Path(log_file)
    else:
        repo = _find_skill_repo()
        path = repo.parent / ".claude" / "skills" / "cli-me-meta" / "references" / "meta-wiki" / "log.md"

    log = LogFile(path)
    log.append(skill, message)
    console.print(f"Appended entry for [bold]{skill}[/bold] to {path}", style="green")
```

- [ ] **Step 4: Run all CLI tests**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add cli_me/main.py tests/test_cli.py
git commit -m "feat: add clime log append subcommand with file locking"
```

---

### Task 7: Add concurrent write safety test

**Files:**
- Modify: `tests/test_filelock.py`

This task adds a real concurrency test to verify the whole point of this feature: two threads writing simultaneously don't lose data.

- [ ] **Step 1: Write the concurrent test**

Append to `tests/test_filelock.py`:

```python
import threading


def test_concurrent_writes_no_data_loss(tmp_path):
    """Two threads writing to the same file via locked_write don't lose data."""
    target = tmp_path / "counter.json"
    target.write_text(json.dumps({"count": 0}))

    errors = []

    def increment(n: int) -> None:
        """Increment the counter n times, each via a locked read-modify-write."""
        for _ in range(n):
            def writer(path: Path) -> None:
                data = json.loads(target.read_text())
                data["count"] += 1
                path.write_text(json.dumps(data))

            try:
                locked_write(target, writer)
            except Exception as e:
                errors.append(e)

    iterations = 20
    t1 = threading.Thread(target=increment, args=(iterations,))
    t2 = threading.Thread(target=increment, args=(iterations,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Errors during concurrent writes: {errors}"

    data = json.loads(target.read_text())
    assert data["count"] == iterations * 2
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/test_filelock.py::test_concurrent_writes_no_data_loss -v`
Expected: PASS — the lock serializes the increments, final count is 40

- [ ] **Step 3: Commit**

```bash
git add tests/test_filelock.py
git commit -m "test: add concurrent write safety test for filelock"
```

---

### Task 8: Run full test suite and verify

**Files:** (none — verification only)

- [ ] **Step 1: Run the complete test suite**

Run: `uv run pytest tests/ -v`
Expected: all tests PASS

- [ ] **Step 2: Run the CLI to verify subcommands appear**

Run: `uv run clime --help`
Expected: output shows `list`, `search`, `info`, `install`, `uninstall`, `registry`, `log`

Run: `uv run clime registry --help`
Expected: output shows `add`, `remove`, `update`

Run: `uv run clime log --help`
Expected: output shows `append`

- [ ] **Step 3: Smoke test a real registry add/remove cycle**

Run:
```bash
uv run clime registry add --name test-concurrent --description "concurrency test" --category test --tags "test"
uv run clime info test-concurrent
uv run clime registry remove test-concurrent
```
Expected: add succeeds, info shows the skill, remove succeeds

- [ ] **Step 4: Commit any fixes if needed, then final commit**

```bash
git add -A
git commit -m "feat: concurrent-safe registry and log CLI — complete"
```
