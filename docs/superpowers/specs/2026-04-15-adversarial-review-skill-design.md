# Adversarial Review Skill Design

**Date:** 2026-04-15
**Status:** Draft

## Problem

cli-me skills go through adversarial review during the build process, but there's
no way to run a full audit on a completed skill after the fact. The review prompts
are embedded in a monolithic `adversarial-reviewers.md` file, making them hard to
reuse from multiple contexts.

We need a standalone audit tool that points at any skill in `skill-repo/` and runs
the full review gauntlet: static checks + all 5 adversarial reviewers.

## Design

### Invocation

```
/adversarial-review yt-dlp
/adversarial-review yt-dlp --fix
```

- Argument is a skill name from `skill-repo/`
- Default mode: report-only (no file modifications)
- `--fix` flag: enables auto-fix loop for objective failures (3-strike limit)

### File Layout

#### Reviewer prompt decomposition

Split the existing monolithic `adversarial-reviewers.md` into individual files.
These stay under `cli-me-meta/references/` as the single source of truth. Both
the new skill and cli-me-meta read from the same files.

```
.claude/skills/cli-me-meta/references/adversarial-reviewers/
├── protocol.md          # Finding categories, fix-review loop, phase gate format
├── r1-wiki-technique.md # Reviewer 1: wiki technique page accuracy
├── r2-scaffold.md       # Reviewer 2: SKILL.md, registry, structure
├── r3-code-wiki.md      # Reviewer 3: code-wiki alignment
├── r4-test-quality.md   # Reviewer 4: test mutation/coverage/depth
└── r5-wiki-execution.md # Reviewer 5: run every documented command
```

The old `adversarial-reviewers.md` is deleted after the split.

#### New skill

```
.claude/skills/adversarial-review/
└── SKILL.md
```

#### New static check tool

```
qa/check_links.py
```

### Skill Flow

#### Phase 1 — Static Checks (sequential, fast)

Run deterministic tools first. These are cheap and catch mechanical issues that
LLM reviewers miss or spot-check.

1. **Link/orphan checker** — `uv run qa/check_links.py <name>`
   - Broken cross-links between markdown files
   - Orphan files not referenced from any markdown file
2. **URL checker** — `uv run qa/check_urls.py <name>`
   - Dead external URLs (404, 403, 5xx, timeout)
3. **Test suite** — `uv run pytest qa/<name>/ -v`
   - Tier 1 (command-graph) and Tier 2 (integration) failures

Static check results are included in the final report and also passed to the
adversarial reviewers as context (so they don't duplicate mechanical checks).

#### Phase 2 — Adversarial Reviewers (parallel agents)

Dispatch all 5 reviewers as fresh subagents simultaneously. Each agent receives:
- The reviewer prompt (read from the decomposed file)
- The skill path (`skill-repo/<name>/`)
- Static check results from Phase 1 (so they can focus on deeper issues)

Each reviewer returns a structured findings report.

#### Phase 3 — Report Assembly

Collect all findings and produce a structured report:

```
## Adversarial Review: yt-dlp

### Static Checks
- Links/Orphans: 0 broken links, 1 orphan file
- URLs: 79 checked, 73 live, 6 dead (all example placeholders)
- Tests: 134 passed, 0 failed

### Reviewer Findings

#### R1 Wiki Technique: NEEDS_REVISION (6 findings)
- [OBJECTIVE] post-processing.md: SponsorBlock claim is factually wrong
- [JUDGMENT] audio-extraction.md: Missing aac vs m4a distinction
...

#### R2 Scaffold: PASS (0 findings)
...

### Summary
- Objective failures: 3
- Judgment calls: 8
- Health score: 7/10

### Judgment Calls for Human Review
1. [R1, audio-extraction.md] "Missing aac vs m4a distinction — minor gap"
   Risk: Low
2. ...
```

#### With `--fix` flag

Phase 3 adds an auto-fix loop:
1. Collect all objective failures
2. For each: dispatch a fix agent (fresh, not the reviewer) with the finding
3. Re-dispatch a fresh agent with the same reviewer prompt to verify the fix
4. Max 3 cycles per finding before escalating to human
5. Present: what was fixed, what was escalated, judgment calls

### Link/Orphan Checker: `qa/check_links.py`

**Usage:** `uv run qa/check_links.py <skill-name>`

**Scope:** Markdown files only. Python import orphans are a separate concern
(caught by test suites and import errors).

**Algorithm:**
1. Walk every `.md` file under `skill-repo/<name>/`
2. Extract all relative markdown links: `[text](path)` and `[text](path#anchor)`
3. For each link, resolve the path relative to the linking file's directory
4. Check if the resolved target exists on disk
5. Build two sets:
   - **All `.md` files** that exist under `skill-repo/<name>/`
   - **Referenced `.md` files** — union of all link targets + root entry points
6. **Broken links** = links whose resolved targets don't exist
7. **Orphan files** = `.md` files that exist but appear in no link from any other `.md` file

**Exclusions from orphan detection:**
- `SKILL.md` (root entry point, loaded by Claude Code directly)
- Non-markdown files (Python, TOML, lock files — discovered via imports, not links)

**Output format:**
```
BROKEN LINKS:
  references/index.md:5 → techniques/video-filters.md (NOT FOUND)

ORPHAN FILES:
  references/techniques/old-draft.md (not linked from any .md file)

SUMMARY: 1 broken link, 1 orphan file
```

**Exit codes:**
- 0: no issues
- 1: broken links or orphans found

### cli-me-meta Update

Update cli-me-meta's SKILL.md to reference the decomposed reviewer files instead
of the monolithic `adversarial-reviewers.md`. The instructions change from
"read the prompt from adversarial-reviewers.md" to "read the prompt from
adversarial-reviewers/r1-wiki-technique.md" etc.

## Out of Scope

- GUI or web dashboard for review results
- Integration with CI/CD pipelines
- Review of non-cli-me skills
- Automated scheduling of reviews
