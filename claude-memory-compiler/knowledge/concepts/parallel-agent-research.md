---
title: Parallel Agent Research and Implementation
tags: [process, agent-patterns]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# Parallel Agent Research and Implementation

Dispatching multiple agents in parallel is the highest-leverage pattern in the cli-me build process. It applies to both research and implementation phases.

## Research Phase

10 parallel agents produced 35 deeply researched technique pages in approximately 5 minutes of wall time during the ffmpeg build. Quality was high — real commands, source URLs, common mistakes documented.

**Caveat:** Research agents cite URLs without verifying them. URLs found in search results may already be dead. A deterministic URL checker must run immediately after wiki pages are written. See [[connections/url-rot-and-research-agents]].

**Caveat:** Adversarial reviewers found 8 factual errors in 10 technique pages during the yt-dlp build — a higher error rate than source-code analysis. Research-generated content requires a review pass. See [[concepts/adversarial-review-system]].

## Implementation Phase

Parallel agent implementation scales well for independent command groups. During the yt-dlp build, three agents implemented info, process, and batch+config groups simultaneously with no conflicts. The split-by-group module architecture enables this cleanly.

## Prerequisites for Parallel Implementation

- Commands must be split into independent groups (one file per group)
- No shared mutable state between groups
- Each agent gets a self-contained brief with the relevant wiki pages

## Scaling Considerations

The R5 adversarial reviewer was updated to dispatch one subagent per technique page instead of running sequentially. The benefit scales with command speed — marginal for demucs (5 seconds per command) but significant for ffmpeg (milliseconds per command).

See also: [[concepts/fresh-context-for-review]], [[playbooks/skill-build-process]].
