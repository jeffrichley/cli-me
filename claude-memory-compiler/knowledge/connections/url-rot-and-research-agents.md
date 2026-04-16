---
title: URL Rot and Research Agents
tags: [process, research, agent-patterns]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# URL Rot and Research Agents

This connection links two patterns: **research agents cite URLs without verifying them** and **URL rot is constant and brutal**.

## The Problem

When [[concepts/parallel-agent-research|parallel research agents]] search the web and write wiki pages, they include URLs from search results. Those URLs may already be dead — the agents cite them from search snippets without fetching the target page. The ffmpeg wiki went from 0% verified dead URLs at creation to 37 dead URLs found on first check. The URLs were already dead when the agents wrote them.

## The Compounding Factor

Research agents also have a higher factual error rate than source-code analysis agents. The R1 adversarial reviewer found 8 factual errors in 10 technique pages during the yt-dlp build. Research-generated content is less reliable than implementation code and requires more aggressive verification.

## The Fix

1. Run the deterministic URL checker immediately after wiki pages are written — before any adversarial review begins. See [[concepts/deterministic-before-llm]].
2. Run the full adversarial review pipeline, which catches semantic errors that URL checking misses.
3. Re-run URL checks periodically, as working URLs can rot over time.

## Implication

The verification step added to Phase 3 of the meta-skill exists specifically because of this pattern. Wiki commands should be verified by running them — research output is a draft, not a source of truth.

See also: [[concepts/adversarial-review-system]], [[concepts/parallel-agent-research]].
