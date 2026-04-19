---
title: Adversarial Review System
tags: [process, review, agent-patterns]
sources: [daily/2026-04-15-seed.md, daily/2026-04-18.md]
created: 2026-04-16
updated: 2026-04-18
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
- **R5:** Execution testing — runs actual API calls and verifies real behavior (dispatches subagents in parallel)

Static checks (link/orphan checker, URL checker, test suite) run before LLM reviewers. See [[concepts/deterministic-before-llm]].

## R5 as the Highest-Value Reviewer

R5 (execution testing) emerged as the most valuable individual reviewer during the pyannote build. By running actual API calls against the installed library, R5 caught behavior mismatches that static analysis and code review could not detect:

- `Pipeline.from_pretrained("pyannote/voice-activity-detection")` is broken in v4.0.4 (cached config format rejected)
- `Inference(window="whole")` returns shape `(256,)` not `(1, 256)` as documented
- RTTM field 2 is `<NA>` for bare Annotation objects without `uri` set

These are the kinds of issues that only surface when code runs against real dependencies. R1 (factual accuracy) and R3 (code-wiki alignment) may flag the same issues from documentation, but only R5 provides ground-truth confirmation.

## Cross-Reviewer Consensus

When multiple independent reviewers flag the same issue through different methods, confidence is very high. During the pyannote review, R1, R3, and R5 all independently identified the embedding shape mismatch — R1 from documentation, R3 from code-wiki comparison, R5 from execution. See [[connections/cross-reviewer-consensus]] for the full analysis.

## Evidence

Round 1 found the runtime crash, dead URLs, and untested commands. Round 2 caught conditional assertion traps. Round 3 found systemic code-wiki divergence. Each round justified its cost. The pyannote build further validated the system: R5 execution testing caught real API behavior mismatches invisible to static review.

See also: [[concepts/fresh-context-for-review]], [[concepts/qa-before-implementation]], [[connections/cross-reviewer-consensus]].
