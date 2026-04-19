---
title: Bootstrap Problem in Self-Referential Systems
tags: [process, tooling, meta]
sources: [daily/2026-04-16.md]
created: 2026-04-18
updated: 2026-04-18
---

# Bootstrap Problem in Self-Referential Systems

When a system references its own artifacts during operation, the first run encounters a chicken-and-egg problem: the artifacts don't exist until the system creates them, but the system expects them to exist before it runs.

## The Memory Compiler Case

The memory compiler's article format templates (`article-formats.md`) are themselves a wiki article. On the first compilation, the compiler tries to read this article to know how to format output — but the article doesn't exist yet because no compilation has run. The "not found" warning on first run is expected and harmless; the article is created during that first compilation and available for all subsequent runs.

## The Pattern

Self-referential bootstrap problems appear whenever:

1. A system consumes its own output as input
2. There is no initial seed state
3. The system treats missing artifacts as warnings rather than fatal errors

The correct design is graceful degradation on first run: warn but continue, create the missing artifacts, and have them available for subsequent runs. Making missing bootstrap artifacts fatal would prevent the system from ever starting.

## Broader Application

This pattern extends beyond the memory compiler. Any agent-driven system that builds up knowledge over time faces the same issue: the first session has no prior knowledge to draw on. Design for cold-start by ensuring the system produces useful output even without prior state.

See also: [[concepts/two-tier-knowledge-routing]], [[concepts/deterministic-before-llm]].
