---
name: swot
description: SWOT analysis of a cli-me build session. Analyzes how the process skills
  performed (cli-me-meta, adversarial-review, reviewer prompts, static checks) and
  proposes concrete patches to improve them. Use when asked to "swot", "session analysis",
  "what should we improve", "process review", "skill improvement", "retrospective on
  the build", or after completing a skill build.
---

# SWOT — Process Skill Improvement Analysis

Analyze how the cli-me process skills performed during this session and propose
concrete improvements to them.

**Key distinction:** This analyzes the PROCESS (cli-me-meta, adversarial-review,
reviewer prompts, static check tools), not the PRODUCT (the skill that was built).
The product is evidence about whether the process worked.

## Phase 1 — Gather Evidence

Read everything holistically. Do not pre-filter — let the analysis decide what matters.

### 1. Session scope

```bash
git log --since="12 hours ago" --oneline
```

This scopes what happened in the current session. Read the full diffs for
commits that touch process-relevant files.

### 2. Process skill files

Read all of these:

- `.claude/skills/cli-me-meta/SKILL.md` — the build process
- `.claude/skills/adversarial-review/SKILL.md` — the audit process
- `.claude/skills/cli-me-meta/references/adversarial-reviewers/protocol.md` — review protocol
- `.claude/skills/cli-me-meta/references/adversarial-reviewers/r1-wiki-technique.md`
- `.claude/skills/cli-me-meta/references/adversarial-reviewers/r2-scaffold.md`
- `.claude/skills/cli-me-meta/references/adversarial-reviewers/r3-code-wiki.md`
- `.claude/skills/cli-me-meta/references/adversarial-reviewers/r4-test-quality.md`
- `.claude/skills/cli-me-meta/references/adversarial-reviewers/r5-wiki-execution.md`

### 3. Static check tools

- `qa/check_links.py` — link/orphan checker
- `qa/check_urls.py` — URL checker
- `qa/conftest.py` — test fixtures and helpers

### 4. Meta-wiki

- `.claude/skills/cli-me-meta/references/meta-wiki/log.md` — accumulated learnings
- `.claude/skills/cli-me-meta/references/meta-wiki/index.md` — knowledge base index

### 5. Built artifacts

Read what was built this session in `skill-repo/`:
- SKILL.md files
- Command logic files in `scripts/`
- Wiki technique pages in `references/`
- Test files in `qa/`
- Gotchas files

### 6. Specs and plans

- `docs/superpowers/specs/` — design specs from this session
- `docs/superpowers/plans/` — implementation plans from this session

## Phase 2 — SWOT Analysis

For each finding, ask: **"What does this tell me about the process skills, and
what should change in them?"**

### Strengths (keep doing these)

Identify what the process got RIGHT. Look for:
- Steps in cli-me-meta that prevented bugs
- Reviewer prompts that caught real issues
- Static checks that found things reviewers missed
- Patterns that made the build faster or higher quality

Each strength needs evidence from the session.

### Weaknesses (fix these)

Identify what the process got WRONG or MISSED. Look for:
- Bugs that made it through the build process and were only caught by adversarial review
- Steps missing from cli-me-meta that caused rework
- Reviewer prompts that missed something they should have caught
- Static checks that had false positives or missed real issues
- Documentation patterns that led to wiki-code divergence

**Each weakness MUST include a concrete patch** — a specific edit to a specific
file that would prevent this weakness in future builds.

### Opportunities (could improve)

Identify improvements suggested by the session but not strictly "wrong." Look for:
- New static checks that would catch classes of issues deterministically
- Reviewer prompt improvements that would focus attention better
- cli-me-meta process steps that could be added or reordered
- Meta-wiki learnings that should be promoted into the process itself
  (a learning that applies to EVERY build should become a step, not just a note)

**Each opportunity MUST include a concrete patch.**

### Threats (watch for these)

Identify patterns that could cause problems at scale. Look for:
- Assumptions in the process that only work for certain types of software
- Reviewer prompts that reference specific patterns that may not generalize
- Steps that get slower or less effective as the skill count grows
- Single points of failure in the process

Threats are informational — no patch required, but flag them clearly.

## Phase 3 — Propose Patches

For each Weakness and Opportunity, the patch format is:

```
**[Title]**
Evidence: [what happened this session]
File: [exact file path]
Section: [which section of the file]

```diff
- [old text if replacing]
+ [new text]
```
```

Patches must be:
- **Specific** ��� exact file, exact location, exact text
- **Minimal** — change only what's needed to address the finding
- **Self-contained** — the patch makes sense without reading the rest of the analysis

## Phase 4 — Present for Approval

Present the full SWOT report with all patches inline. Then ask the user to
approve or reject each patch individually.

Format the approval request as a numbered list:

```
## Proposed Changes

1. [Weakness: title] → patch to [file]
2. [Weakness: title] → patch to [file]
3. [Opportunity: title] → patch to [file]
...

Which patches should I apply? (e.g., "all", "1,2,4", "all except 3")
```

Apply approved patches, commit with:
```
git commit -m "improve(process): apply SWOT findings from [session date]"
```

## Important

- **Never patch product skills.** Only patch process skills (cli-me-meta,
  adversarial-review, reviewer prompts, static check tools, conftest.py).
- **Evidence required.** Every finding must cite something specific from the session.
  No hypothetical findings.
- **Patches over prose.** A diff is worth a thousand words. Don't describe what
  should change — show the change.
- **Promote repeated learnings.** If a meta-wiki log entry describes something
  that applies to every build, the SWOT should propose promoting it from a
  log note to an actual process step in cli-me-meta.
