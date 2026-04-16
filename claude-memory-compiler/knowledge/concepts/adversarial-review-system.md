---
title: Adversarial Review System
tags: [process, review, agent-patterns]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# Adversarial Review System

The adversarial review system finds defects that build processes miss. Three full rounds on the ffmpeg skill found: a runtime crash bug, 78% dead URLs, 51% untested commands, systemic code-wiki divergence, and false-confidence tests. None were caught during the build.

## Objective vs Judgment Split

The most critical architectural decision: separating objective failures from judgment calls.

- **Objective failures** (wrong flags, dead URLs, crash bugs): Enter an auto-fix loop with a 3-strike limit. Reviewer finds issue, fix agent fixes, reviewer re-verifies. If the same issue persists after 3 cycles, escalate to human.
- **Judgment calls** (is this best practice actually best?): Accumulate for human decision at phase boundaries.

Without this split, the process either blocks forever on debatable issues or rubber-stamps everything to avoid blocking.

## Code-Wiki Alignment (R3)

The highest-value review category. R3 cross-references implementation code against wiki/reference documentation and finds divergence. Systemic patterns discovered:

- Audio bitrate: code used 128k, wiki documented 192k
- Missing `pix_fmt` specifications
- Missing `lanczos` scaling algorithm
- Missing H.264 `profile`/`level` flags

**Pattern:** Agents write code that "works" but uses weaker settings than what the wiki documents. Always cross-reference code against reference material.

## Five Reviewers

The system uses 5 specialized reviewers (R1-R5), decomposed into individual prompt files:

- **R1:** Factual accuracy and error detection
- **R2:** CLI behavior and edge cases (caught the `-y` flag issue — see [[connections/interactive-prompts-in-agent-context]])
- **R3:** Code-wiki alignment
- **R4:** Test coverage and assertion quality (see [[concepts/assertion-depth]])
- **R5:** Technique page verification (dispatches subagents in parallel)

Static checks (link/orphan checker, URL checker, test suite) run before LLM reviewers. See [[concepts/deterministic-before-llm]].

## Evidence

Round 1 found the runtime crash, dead URLs, and untested commands. Round 2 caught conditional assertion traps. Round 3 found systemic code-wiki divergence. Each round justified its cost.

See also: [[concepts/fresh-context-for-review]], [[concepts/qa-before-implementation]].
