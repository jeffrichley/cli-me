"""Markdown link and orphan file checker for cli-me skills.

Checks two things:
1. All relative markdown links resolve to existing files
2. No .md files are orphaned (unreferenced by any other .md file)

Usage:
    uv run qa/check_links.py                  # check all skills
    uv run qa/check_links.py yt-dlp           # check one skill
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


SKILL_REPO = Path(__file__).parent.parent / "skill-repo"

LINK_PATTERN = re.compile(
    r'\[([^\]]*)\]'
    r'\('
    r'(?!https?://)'
    r'(?!/)'
    r'([^)#\s]+)'
    r'(?:#([^)\s]*))?'
    r'\)'
)

ORPHAN_EXCLUDES = {"SKILL.md", "index.md"}


def find_md_files(root: Path) -> list[Path]:
    """Find all .md files under root."""
    return sorted(root.rglob("*.md"))


def extract_relative_links(text: str) -> list[tuple[str, str | None]]:
    """Extract relative markdown links from text.
    Returns list of (path, anchor_or_None).
    """
    results = []
    for match in LINK_PATTERN.finditer(text):
        path = match.group(2)
        anchor = match.group(3) if match.group(3) else None
        results.append((path, anchor))
    return results


def check_links(root: Path) -> list[dict]:
    """Find all broken relative links in .md files under root.
    Returns list of dicts with keys: source, line, target, resolved.
    """
    broken = []
    for md_file in find_md_files(root):
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for line_num, line in enumerate(text.splitlines(), 1):
            for path, _anchor in extract_relative_links(line):
                resolved = (md_file.parent / path).resolve()
                if not resolved.exists():
                    broken.append({
                        "source": str(md_file.relative_to(root)),
                        "line": line_num,
                        "target": path,
                        "resolved": str(resolved),
                    })
    return broken


def check_orphans(root: Path) -> list[str]:
    """Find .md files that no other .md file links to.
    Returns list of relative paths of orphaned files.
    """
    md_files = find_md_files(root)

    referenced: set[Path] = set()
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for path, _anchor in extract_relative_links(text):
            resolved = (md_file.parent / path).resolve()
            referenced.add(resolved)

    orphans = []
    for md_file in md_files:
        rel = str(md_file.relative_to(root))
        if md_file.name in ORPHAN_EXCLUDES:
            continue
        if md_file.resolve() not in referenced:
            orphans.append(rel)

    return sorted(orphans)


def check_skill(skill_name: str) -> tuple[list[dict], list[str]]:
    """Run both checks on a skill. Returns (broken_links, orphan_files)."""
    skill_dir = SKILL_REPO / skill_name
    if not skill_dir.exists():
        print(f"Skill directory not found: {skill_dir}")
        return [], []

    broken = check_links(skill_dir)
    orphans = check_orphans(skill_dir)
    return broken, orphans


def main() -> int:
    skill_filter = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None

    if skill_filter:
        skills = [skill_filter]
    else:
        skills = sorted(
            d.name for d in SKILL_REPO.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )

    total_broken = 0
    total_orphans = 0

    for skill in skills:
        print(f"\n{'='*60}")
        print(f"Checking links: {skill}")
        print(f"{'='*60}")

        broken, orphans = check_skill(skill)

        if broken:
            print(f"\nBROKEN LINKS:")
            for b in broken:
                print(f"  {b['source']}:{b['line']} -> {b['target']} (NOT FOUND)")
            total_broken += len(broken)
        else:
            print(f"\n  No broken links.")

        if orphans:
            print(f"\nORPHAN FILES:")
            for o in orphans:
                print(f"  {o} (not linked from any .md file)")
            total_orphans += len(orphans)
        else:
            print(f"  No orphan files.")

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Broken links:  {total_broken}")
    print(f"  Orphan files:  {total_orphans}")

    return 1 if (total_broken + total_orphans) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
