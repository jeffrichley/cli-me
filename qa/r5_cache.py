"""R5 wiki execution cache — skip R5 if technique files and code haven't changed.

Computes a SHA-256 hash of all technique pages and command source files for a skill.
Stores the hash in qa/<skill-name>/.r5-cache.json. On subsequent runs, compares the
current hash to the cached one. If unchanged, R5 can be skipped.

Usage:
    uv run qa/r5_cache.py check <skill-name>    # exit 0 if unchanged, exit 1 if changed
    uv run qa/r5_cache.py update <skill-name>    # update the cache after a successful R5 run
    uv run qa/r5_cache.py show <skill-name>      # print cache status
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skill-repo"
QA_DIR = REPO_ROOT / "qa"


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_hash(skill_name: str) -> str:
    """Compute a combined hash of technique pages + command source files."""
    skill_path = SKILL_DIR / skill_name
    hasher = hashlib.sha256()

    # Technique pages
    techniques_dir = skill_path / "references" / "techniques"
    if techniques_dir.exists():
        for f in sorted(techniques_dir.glob("*.md")):
            hasher.update(f.read_bytes())

    # Command source files
    commands_dir = skill_path / "scripts" / f"{skill_name.replace('-', '_')}_cli" / "commands"
    if commands_dir.exists():
        for f in sorted(commands_dir.glob("*.py")):
            hasher.update(f.read_bytes())

    # CLI wrappers
    cli_dir = skill_path / "scripts" / f"{skill_name.replace('-', '_')}_cli"
    if cli_dir.exists():
        for f in sorted(cli_dir.glob("*.py")):
            if f.parent == cli_dir:  # top-level only, not commands/
                hasher.update(f.read_bytes())

    # SKILL.md
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        hasher.update(skill_md.read_bytes())

    return hasher.hexdigest()


def cache_path(skill_name: str) -> Path:
    return QA_DIR / skill_name / ".r5-cache.json"


def read_cache(skill_name: str) -> dict | None:
    path = cache_path(skill_name)
    if path.exists():
        return json.loads(path.read_text())
    return None


def write_cache(skill_name: str, hash_value: str) -> None:
    path = cache_path(skill_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hash": hash_value}, indent=2) + "\n")


def check(skill_name: str) -> bool:
    """Return True if files are unchanged since last R5 run."""
    cached = read_cache(skill_name)
    if cached is None:
        return False
    current = compute_hash(skill_name)
    return cached["hash"] == current


def update(skill_name: str) -> None:
    """Update the cache with the current file hash."""
    current = compute_hash(skill_name)
    write_cache(skill_name, current)


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: r5_cache.py <check|update|show> <skill-name>")
        sys.exit(2)

    action = sys.argv[1]
    skill_name = sys.argv[2]

    if action == "check":
        if check(skill_name):
            print(f"R5 SKIP: {skill_name} technique files unchanged since last R5 run.")
            sys.exit(0)
        else:
            print(f"R5 NEEDED: {skill_name} technique files have changed (or no cache).")
            sys.exit(1)
    elif action == "update":
        update(skill_name)
        print(f"R5 cache updated for {skill_name}.")
    elif action == "show":
        cached = read_cache(skill_name)
        current = compute_hash(skill_name)
        if cached is None:
            print(f"No R5 cache for {skill_name}.")
        elif cached["hash"] == current:
            print(f"R5 cache for {skill_name}: UP TO DATE (hash: {current[:12]}...)")
        else:
            print(f"R5 cache for {skill_name}: STALE")
            print(f"  Cached: {cached['hash'][:12]}...")
            print(f"  Current: {current[:12]}...")
    else:
        print(f"Unknown action: {action}")
        sys.exit(2)


if __name__ == "__main__":
    main()
