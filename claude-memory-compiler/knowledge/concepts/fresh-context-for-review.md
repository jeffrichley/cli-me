---
title: Fresh Context for Review
tags: [process, review, agent-patterns]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# Fresh Context for Review

Reviewer agents must have zero context from the creator's session. The same agent that built the code will rationalize its own mistakes. A different model is even better (creator: Sonnet, reviewer: Opus, or vice versa).

## Why Fresh Context Matters

When an agent reviews its own work, it carries implicit assumptions about what it intended. These assumptions cause it to read code as correct even when it isn't — the agent fills in gaps from memory rather than from what's actually written.

This was validated across three rounds of adversarial review on the ffmpeg skill. Issues found by fresh-context reviewers were consistently invisible to the original builder.

## Implementation

The adversarial review system enforces this by:

1. Dispatching reviewer agents with no conversation history from the build
2. Providing only the artifacts (code, wiki pages, tests) — never the build rationale
3. Using a different model when possible for additional cognitive diversity

## Relationship to Adversarial Reviews

Fresh context is a prerequisite for effective [[concepts/adversarial-review-system|adversarial review]]. The entire objective/judgment split, the 3-strike auto-fix loop, and the code-wiki alignment checks all depend on reviewers seeing the work without the creator's bias.

## The Standalone Skill

The adversarial review system was decomposed from a monolithic `adversarial-reviewers.md` into `protocol.md` + 5 individual reviewer prompt files (r1-r5). Both the cli-me-meta skill and the standalone `/adversarial-review` skill read from the same files — single source of truth.

See also: [[concepts/adversarial-review-system]], [[concepts/deterministic-before-llm]].
