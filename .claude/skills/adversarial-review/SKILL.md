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
