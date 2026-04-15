# Adversarial Review Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a standalone `/adversarial-review <skill-name>` skill that runs static checks + all 5 adversarial reviewers against any completed cli-me skill, with an optional `--fix` mode.

**Architecture:** A Claude Code skill (SKILL.md) orchestrates three phases: deterministic static checks (link/orphan checker, URL checker, test suite), parallel adversarial reviewer dispatch (5 fresh agents reading decomposed prompt files), and report assembly. The reviewer prompts are split from the monolithic `adversarial-reviewers.md` into individual files so both this skill and cli-me-meta share one source of truth.

**Tech Stack:** Claude Code skill (SKILL.md), Python scripts (check_links.py), pytest, Agent tool for reviewer dispatch.

---

### Task 1: Build the link/orphan checker

**Files:**
- Create: `qa/check_links.py`

- [ ] **Step 1: Write the test for broken link detection**

Create `qa/test_check_links.py`:

```python
"""Tests for the markdown link/orphan checker."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_links import find_md_files, extract_relative_links, check_links, check_orphans


class TestExtractRelativeLinks:
    def test_standard_link(self):
        links = extract_relative_links("[Foo](bar.md)")
        assert links == [("bar.md", None)]

    def test_link_with_anchor(self):
        links = extract_relative_links("[Foo](bar.md#section)")
        assert links == [("bar.md", "section")]

    def test_ignores_http_urls(self):
        links = extract_relative_links("[Foo](https://example.com)")
        assert links == []

    def test_ignores_absolute_paths(self):
        links = extract_relative_links("[Foo](/absolute/path.md)")
        assert links == []

    def test_multiple_links(self):
        text = "[A](a.md) some text [B](sub/b.md)"
        links = extract_relative_links(text)
        assert ("a.md", None) in links
        assert ("sub/b.md", None) in links

    def test_parent_directory_link(self):
        links = extract_relative_links("[Up](../other.md)")
        assert links == [("../other.md", None)]


class TestCheckLinks:
    def test_valid_link(self, tmp_path):
        index = tmp_path / "index.md"
        target = tmp_path / "page.md"
        index.write_text("[Page](page.md)")
        target.write_text("# Page")

        broken = check_links(tmp_path)
        assert broken == []

    def test_broken_link(self, tmp_path):
        index = tmp_path / "index.md"
        index.write_text("[Missing](missing.md)")

        broken = check_links(tmp_path)
        assert len(broken) == 1
        assert broken[0]["target"] == "missing.md"
        assert "index.md" in broken[0]["source"]

    def test_subdirectory_link(self, tmp_path):
        index = tmp_path / "index.md"
        sub = tmp_path / "sub"
        sub.mkdir()
        target = sub / "page.md"
        index.write_text("[Sub](sub/page.md)")
        target.write_text("# Sub page")

        broken = check_links(tmp_path)
        assert broken == []

    def test_broken_subdirectory_link(self, tmp_path):
        index = tmp_path / "index.md"
        index.write_text("[Sub](sub/missing.md)")

        broken = check_links(tmp_path)
        assert len(broken) == 1


class TestCheckOrphans:
    def test_no_orphans(self, tmp_path):
        index = tmp_path / "index.md"
        page = tmp_path / "page.md"
        index.write_text("[Page](page.md)")
        page.write_text("# Page")

        orphans = check_orphans(tmp_path)
        assert orphans == []

    def test_finds_orphan(self, tmp_path):
        index = tmp_path / "index.md"
        page = tmp_path / "page.md"
        orphan = tmp_path / "forgotten.md"
        index.write_text("[Page](page.md)")
        page.write_text("# Page")
        orphan.write_text("# I am lost")

        orphans = check_orphans(tmp_path)
        assert len(orphans) == 1
        assert "forgotten.md" in orphans[0]

    def test_excludes_skill_md(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        index = tmp_path / "index.md"
        skill.write_text("# Skill")
        index.write_text("nothing links here but index is a root")

        orphans = check_orphans(tmp_path)
        # SKILL.md should never be reported as orphan
        assert not any("SKILL.md" in o for o in orphans)

    def test_mutually_linked_files(self, tmp_path):
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        a.write_text("[B](b.md)")
        b.write_text("[A](a.md)")

        orphans = check_orphans(tmp_path)
        assert orphans == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest qa/test_check_links.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'check_links'`

- [ ] **Step 3: Implement check_links.py**

Create `qa/check_links.py`:

```python
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

# Matches [text](relative/path.md) and [text](relative/path.md#anchor)
# Excludes http(s):// and absolute paths starting with /
LINK_PATTERN = re.compile(
    r'\[([^\]]*)\]'           # [link text]
    r'\('                      # (
    r'(?!https?://)'           # not http(s)://
    r'(?!/)'                   # not absolute path
    r'([^)#\s]+)'              # path (no spaces, no #, no ))
    r'(?:#([^)\s]*))?'         # optional #anchor
    r'\)'                      # )
)

# Files excluded from orphan detection
ORPHAN_EXCLUDES = {"SKILL.md"}


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
    all_md_paths = {f.resolve() for f in md_files}

    # Collect all referenced paths
    referenced: set[Path] = set()
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for path, _anchor in extract_relative_links(text):
            resolved = (md_file.parent / path).resolve()
            referenced.add(resolved)

    # Every file is implicitly referenced by itself (it exists),
    # but orphan = not referenced by ANY OTHER file
    orphans = []
    for md_file in md_files:
        rel = str(md_file.relative_to(root))
        # Skip excluded files
        if md_file.name in ORPHAN_EXCLUDES:
            continue
        # Check if any other file links to this one
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
                print(f"  {b['source']}:{b['line']} → {b['target']} (NOT FOUND)")
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest qa/test_check_links.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Run against real skills to verify**

Run: `uv run qa/check_links.py yt-dlp`
Run: `uv run qa/check_links.py ffmpeg`
Expected: Output shows broken links / orphans or clean bill of health. Review output for correctness.

- [ ] **Step 6: Commit**

```bash
git add qa/check_links.py qa/test_check_links.py
git commit -m "feat: add markdown link/orphan checker for cli-me skills"
```

---

### Task 2: Decompose adversarial-reviewers.md into individual files

**Files:**
- Create: `.claude/skills/cli-me-meta/references/adversarial-reviewers/protocol.md`
- Create: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r1-wiki-technique.md`
- Create: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r2-scaffold.md`
- Create: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r3-code-wiki.md`
- Create: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r4-test-quality.md`
- Create: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r5-wiki-execution.md`
- Delete: `.claude/skills/cli-me-meta/references/adversarial-reviewers.md`
- Modify: `.claude/skills/cli-me-meta/SKILL.md` (update references)
- Modify: `.claude/skills/cli-me-meta/references/meta-wiki/index.md` (update link)

- [ ] **Step 1: Create the adversarial-reviewers directory**

```bash
mkdir -p .claude/skills/cli-me-meta/references/adversarial-reviewers
```

- [ ] **Step 2: Extract protocol.md**

Read the existing `adversarial-reviewers.md`. Extract lines 1–108 (everything before `## Reviewer 1`) into `protocol.md`. This includes:
- Core principle
- Finding categories (Objective Failures vs Judgment Calls)
- Fix-Review Loop
- Rules (3-strike limit, reviewer never fixes, judgment calls accumulate, zero-findings flag, phase gate, fix agent instructions)
- Human Checkpoint Format

Write to: `.claude/skills/cli-me-meta/references/adversarial-reviewers/protocol.md`

- [ ] **Step 3: Extract r1-wiki-technique.md**

Extract lines 112–203 (the `## Reviewer 1: Wiki Technique Page Reviewer` section). Include the `**When:**` and `**Dispatch as:**` lines, then the full prompt from inside the code fence.

Write to: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r1-wiki-technique.md`

- [ ] **Step 4: Extract r2-scaffold.md**

Extract lines 207–293 (the `## Reviewer 2: Scaffold Reviewer` section).

Write to: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r2-scaffold.md`

- [ ] **Step 5: Extract r3-code-wiki.md**

Extract lines 297–375 (the `## Reviewer 3: Code-Wiki Alignment Reviewer` section).

Write to: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r3-code-wiki.md`

- [ ] **Step 6: Extract r4-test-quality.md**

Extract lines 379–463 (the `## Reviewer 4: Test Quality Reviewer` section).

Write to: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r4-test-quality.md`

- [ ] **Step 7: Extract r5-wiki-execution.md**

Extract lines 468–549 (the `## Reviewer 5: Wiki Execution Reviewer` section). Also include the Dispatch Notes section (lines 553–565) as a footer since it contains guidance relevant to all reviewers.

Write to: `.claude/skills/cli-me-meta/references/adversarial-reviewers/r5-wiki-execution.md`

- [ ] **Step 8: Verify all content is preserved**

Read the original `adversarial-reviewers.md` and all 6 new files. Verify no content was lost or duplicated. Every line from the original should appear in exactly one new file.

- [ ] **Step 9: Update cli-me-meta SKILL.md references**

In `.claude/skills/cli-me-meta/SKILL.md`, replace all occurrences of:
- `references/adversarial-reviewers.md` → `references/adversarial-reviewers/protocol.md`
- BUT when referencing a specific reviewer (e.g., "Reviewer 1: Wiki Technique Page Reviewer"), point to the specific file (e.g., `references/adversarial-reviewers/r1-wiki-technique.md`)

There are 6 references to update:
1. Line 30: general reference → `references/adversarial-reviewers/protocol.md`
2. Line 90: R1 reference → `references/adversarial-reviewers/r1-wiki-technique.md`
3. Line 180: R2 reference → `references/adversarial-reviewers/r2-scaffold.md`
4. Line 255: R3 reference → `references/adversarial-reviewers/r3-code-wiki.md`
5. Line 262: R4 reference → `references/adversarial-reviewers/r4-test-quality.md`
6. Line 274: R5 reference → `references/adversarial-reviewers/r5-wiki-execution.md`

- [ ] **Step 10: Update meta-wiki/index.md**

Replace the adversarial reviewers link:
```markdown
- [Adversarial Review Prompts](../adversarial-reviewers.md) — 5 reviewer prompts + result handling protocol
```
With:
```markdown
- [Adversarial Review Protocol](../adversarial-reviewers/protocol.md) — finding categories, fix-review loop, phase gate format
- [R1 Wiki Technique](../adversarial-reviewers/r1-wiki-technique.md) — technique page accuracy reviewer
- [R2 Scaffold](../adversarial-reviewers/r2-scaffold.md) — SKILL.md, registry, structure reviewer
- [R3 Code-Wiki](../adversarial-reviewers/r3-code-wiki.md) — code-wiki alignment reviewer
- [R4 Test Quality](../adversarial-reviewers/r4-test-quality.md) — test mutation/coverage/depth reviewer
- [R5 Wiki Execution](../adversarial-reviewers/r5-wiki-execution.md) — run every documented command reviewer
```

- [ ] **Step 11: Delete the old monolithic file**

```bash
rm .claude/skills/cli-me-meta/references/adversarial-reviewers.md
```

- [ ] **Step 12: Run check_links.py against cli-me-meta**

The decomposed files live under `cli-me-meta/references/`, not under `skill-repo/`. The link checker scopes to `skill-repo/`, so this is a manual verification:

Verify all 6 links in `meta-wiki/index.md` resolve correctly:
```bash
ls .claude/skills/cli-me-meta/references/adversarial-reviewers/
```
Expected: `protocol.md  r1-wiki-technique.md  r2-scaffold.md  r3-code-wiki.md  r4-test-quality.md  r5-wiki-execution.md`

- [ ] **Step 13: Commit**

```bash
git add .claude/skills/cli-me-meta/references/adversarial-reviewers/
git add .claude/skills/cli-me-meta/SKILL.md
git add .claude/skills/cli-me-meta/references/meta-wiki/index.md
git rm .claude/skills/cli-me-meta/references/adversarial-reviewers.md
git commit -m "refactor: decompose adversarial-reviewers.md into individual reviewer files"
```

---

### Task 3: Create the adversarial-review skill

**Files:**
- Create: `.claude/skills/adversarial-review/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

Create `.claude/skills/adversarial-review/SKILL.md`:

```markdown
---
name: adversarial-review
description: Run a full adversarial audit on a cli-me skill. Runs static checks
  (link/orphan checker, URL checker, test suite) then dispatches all 5 adversarial
  reviewers in parallel. Use when asked to "review a skill", "audit a skill",
  "adversarial review", "check skill quality", or "run reviewers on". Pass --fix
  to auto-fix objective failures.
---

# Adversarial Review — cli-me skill audit

Full audit of a completed cli-me skill. Runs deterministic static checks first,
then dispatches 5 fresh adversarial reviewer agents in parallel.

## Arguments

- First argument: skill name (e.g., `yt-dlp`, `ffmpeg`)
- `--fix`: enable auto-fix loop for objective failures (default: report-only)

The skill name must match a directory under `skill-repo/`.

## Phase 1 — Static Checks

Run these three checks sequentially. Capture all output for the final report.

### 1. Link/Orphan Checker

```bash
uv run qa/check_links.py <skill-name>
```

Reports: broken cross-links between .md files, orphan .md files not referenced
by any other .md file.

### 2. URL Checker

```bash
uv run qa/check_urls.py <skill-name>
```

Reports: dead external URLs (404, 403, 5xx, timeout).

### 3. Test Suite

```bash
uv run pytest qa/<skill-name>/ -v
```

Reports: Tier 1 (command-graph) and Tier 2 (integration) test failures.

## Phase 2 — Adversarial Reviewers

Read the review protocol from:
`.claude/skills/cli-me-meta/references/adversarial-reviewers/protocol.md`

Dispatch all 5 reviewers as **fresh subagents in parallel** using the Agent tool.
Each agent must have ZERO context from this session — fresh context only.

For each reviewer, read its prompt file and dispatch:

| Reviewer | Prompt file | What it checks |
|----------|-------------|----------------|
| R1 | `adversarial-reviewers/r1-wiki-technique.md` | Wiki technique page accuracy, URLs, completeness |
| R2 | `adversarial-reviewers/r2-scaffold.md` | SKILL.md, registry, directory structure |
| R3 | `adversarial-reviewers/r3-code-wiki.md` | Code matches wiki documentation |
| R4 | `adversarial-reviewers/r4-test-quality.md` | Test mutation resilience, assertion depth |
| R5 | `adversarial-reviewers/r5-wiki-execution.md` | Run every documented command |

When dispatching each agent, provide:
1. The reviewer prompt (read from the file above)
2. The skill path: `skill-repo/<skill-name>/`
3. The test path: `qa/<skill-name>/`
4. Static check results from Phase 1 (so they skip mechanical checks already done)
5. Instruction: "Report findings using the format specified in your prompt.
   Categorize each finding as [OBJECTIVE] or [JUDGMENT]."

## Phase 3 — Report Assembly

Collect all findings and present a structured report:

```
## Adversarial Review: <skill-name>

### Static Checks
- Links/Orphans: N broken links, N orphan files
- URLs: N checked, N live, N dead
- Tests: N passed, N failed

### Reviewer Findings

#### R1 Wiki Technique: PASS / NEEDS_REVISION / FAIL (N findings)
- [OBJECTIVE] file.md: description
- [JUDGMENT] file.md: description

#### R2 Scaffold: PASS / NEEDS_REVISION / FAIL (N findings)
...

(repeat for R3, R4, R5)

### Summary
- Objective failures: N
- Judgment calls: N
- Reviewers with zero findings: [list] (suspicious — noted)

### Judgment Calls for Human Review
1. [R#, file] "description"
   Evidence: [reference]
   Risk: Low / Medium / High
```

### Zero-findings handling

If any reviewer returns zero findings, note it as suspicious in the report.
Do NOT automatically re-dispatch — just flag it so the human can decide.

## With --fix Flag

After assembling the report, enter the fix loop for objective failures only:

1. Read the fix-review protocol from `protocol.md`
2. For each objective failure:
   a. Dispatch a fresh FIX AGENT with the finding details (file path, line,
      what's wrong, what correct behavior should be)
   b. Do NOT provide the reviewer's suggested fix
   c. After the fix, dispatch a fresh agent with the SAME reviewer prompt
      to verify the fix
   d. If still failing, loop (max 3 cycles per finding)
   e. After 3 failures, escalate to human
3. Present final report showing: what was fixed, what was escalated,
   and all judgment calls

## Important

- **Fresh context is non-negotiable.** Never reuse agents across reviewers.
- **Reviewers never fix.** They report. Fix agents fix. Reviewers re-verify.
- **Judgment calls go to the human.** Never auto-resolve judgment calls.
- **Static checks run first** because they're fast, deterministic, and their
  results help reviewers focus on deeper issues.
```

- [ ] **Step 2: Verify the skill loads**

Test that Claude Code can see the new skill by checking the skills directory:
```bash
ls .claude/skills/adversarial-review/
```
Expected: `SKILL.md`

- [ ] **Step 3: Verify prompt file paths resolve**

Check that all referenced prompt files exist:
```bash
ls .claude/skills/cli-me-meta/references/adversarial-reviewers/protocol.md
ls .claude/skills/cli-me-meta/references/adversarial-reviewers/r1-wiki-technique.md
ls .claude/skills/cli-me-meta/references/adversarial-reviewers/r2-scaffold.md
ls .claude/skills/cli-me-meta/references/adversarial-reviewers/r3-code-wiki.md
ls .claude/skills/cli-me-meta/references/adversarial-reviewers/r4-test-quality.md
ls .claude/skills/cli-me-meta/references/adversarial-reviewers/r5-wiki-execution.md
```
Expected: All 6 files exist (created in Task 2).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/adversarial-review/SKILL.md
git commit -m "feat: add adversarial-review skill for standalone skill audits"
```

---

### Task 4: Smoke test the full pipeline

- [ ] **Step 1: Run the link checker against yt-dlp**

```bash
uv run qa/check_links.py yt-dlp
```

Review output. Fix any broken links or orphans found.

- [ ] **Step 2: Run the link checker against ffmpeg**

```bash
uv run qa/check_links.py ffmpeg
```

Review output. Fix any broken links or orphans found.

- [ ] **Step 3: Run the URL checker against yt-dlp**

```bash
uv run qa/check_urls.py yt-dlp
```

Verify output matches expectations (example placeholder URLs are known dead, source URLs are live).

- [ ] **Step 4: Run the full test suite for yt-dlp**

```bash
uv run pytest qa/yt-dlp/ -v
```

Expected: 134 passed (or current count).

- [ ] **Step 5: Dry-run the skill mentally**

Read through the SKILL.md and trace through what would happen if you invoked `/adversarial-review yt-dlp`:
1. Would Phase 1 commands work? (check_links.py, check_urls.py, pytest)
2. Can the skill read the prompt files? (verify paths from SKILL.md match actual file locations)
3. Is the report format clear and actionable?

- [ ] **Step 6: Fix any issues found, commit**

```bash
git add -A
git commit -m "fix: address issues found during adversarial-review smoke test"
```

(Skip this step if no issues found.)

---

### Task 5: Final cleanup and documentation

**Files:**
- Modify: `.claude/skills/cli-me-meta/references/meta-wiki/log.md`

- [ ] **Step 1: Update the meta-wiki log**

Append to `.claude/skills/cli-me-meta/references/meta-wiki/log.md`:

```markdown

27. **Decomposed adversarial-reviewers.md into individual files.** Split the
    monolithic file into protocol.md + 5 reviewer prompt files (r1–r5). Both
    cli-me-meta and the new adversarial-review skill read from the same files.
    Single source of truth for reviewer prompts.

28. **Created standalone adversarial-review skill.** `/adversarial-review <name>`
    runs static checks (link/orphan checker, URL checker, test suite) then
    dispatches all 5 reviewers in parallel. Report-only by default, --fix for
    auto-fix loop. Catches issues that build-time reviews miss because the
    skill has evolved since it was built.

29. **Link/orphan checker catches invisible files.** A markdown file that no
    other markdown file links to is invisible to LLM agents — they'll never
    discover it. The deterministic checker finds these instantly. Scoped to
    .md files only; Python orphans are caught by imports and test suites.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/cli-me-meta/references/meta-wiki/log.md
git commit -m "docs(meta-skill): log adversarial-review skill and link checker learnings"
```
