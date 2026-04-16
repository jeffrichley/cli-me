# SWOT Skill Design

**Date:** 2026-04-15
**Status:** Draft

## Problem

After building a cli-me skill, the process skills (cli-me-meta, adversarial-review,
reviewer prompts, static check tools) may have gaps, missed steps, or missed
opportunities that the session exposed. There's no structured way to turn session
experience into concrete improvements to the process itself.

## Design

### Invocation

```
/swot
```

No arguments. Analyzes the current session in the current repo.

### Trigger Phrases

"swot", "session analysis", "what should we improve", "process review",
"skill improvement", "retrospective on the build"

### Flow

1. **Gather evidence** — read everything holistically
2. **SWOT analysis** — categorize findings about the process skills
3. **Propose patches** — concrete edits for each Weakness and Opportunity
4. **Present for approval** — user approves/rejects each patch

### Key Distinction

The skill analyzes the **process** (how cli-me-meta and adversarial-review performed),
not the **product** (the skill that was built). The product is evidence about whether
the process worked.

### What It Reads

Discovery order (reads everything, no pre-filtering):

1. **Git history** — `git log --since="12 hours ago" --oneline` to scope the session,
   then full diffs for what changed
2. **Process skill files** — everything under `.claude/skills/` (cli-me-meta,
   adversarial-review, reviewer prompts, protocol)
3. **Static check tools** — `qa/check_links.py`, `qa/check_urls.py`, `qa/conftest.py`
4. **Meta-wiki** — `cli-me-meta/references/meta-wiki/log.md` and `index.md`
5. **Built artifacts** — whatever is in `skill-repo/` (the product skills), their
   test files in `qa/`, their wiki pages
6. **Specs and plans** — `docs/superpowers/specs/` and `docs/superpowers/plans/`

### SWOT Categories

Applied to the process skills specifically:

- **Strengths** — what worked well this session. Keep doing these. Evidence-backed.
- **Weaknesses** — what the process got wrong or missed. Each includes a concrete
  patch to the relevant skill file.
- **Opportunities** — improvements that could be added. Each includes a concrete
  patch to the relevant skill file.
- **Threats** — patterns that could cause problems at scale or in future builds.
  Informational, no patch required.

### Output Format

```markdown
## SWOT Analysis: cli-me Session YYYY-MM-DD

### Strengths (keep doing these)
1. **[title]**
   Evidence: [what happened that shows this worked]

### Weaknesses (fix these)
1. **[title]**
   Evidence: [what happened that exposed this]
   Patch: [which file, which section]
   ```diff
   + [concrete addition or change]
   ```

### Opportunities (could improve)
1. **[title]**
   Evidence: [what happened that suggests this]
   Patch: [which file, which section]
   ```diff
   + [concrete addition or change]
   ```

### Threats (watch for these)
1. **[title]**
   Evidence: [what pattern was observed]
```

### Approval Flow

After presenting the report, the user approves or rejects each patch individually.
Approved patches are applied and committed. Rejected patches are noted but not applied.

### Where It Lives

```
.claude/skills/swot/
└── SKILL.md
```

Single-file skill. No supporting files — it reads from the existing project structure.

## Out of Scope

- Analyzing product skill quality (use /adversarial-review for that)
- Cross-session trend analysis
- Automated scheduling
