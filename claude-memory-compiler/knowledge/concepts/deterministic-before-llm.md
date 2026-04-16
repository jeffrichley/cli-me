---
title: Deterministic Tools Before LLM Reviewers
tags: [process, review, tooling]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# Deterministic Tools Before LLM Reviewers

For anything mechanically checkable — URLs, file existence, format validation, link integrity, orphan detection — use a deterministic script. Reserve LLM reviewers for semantic issues that require judgment.

## The Evidence

Three rounds of 5 LLM reviewers (15 total reviews) on the ffmpeg skill caught approximately 5 dead URLs per round. A single run of `qa/check_urls.py` found all 37. LLM reviewers spot-check; deterministic tools check everything.

## Deterministic Checks in cli-me

The following checks run before LLM reviewers in the adversarial review pipeline:

1. **Link/orphan checker** — Finds markdown files that no other markdown file links to. A file invisible to link traversal is invisible to LLM agents. Scoped to `.md` files only. Conventional entry points (`index.md`, `SKILL.md`) are excluded from orphan detection as root nodes.

2. **URL checker** — Verifies all URLs in source/reference sections. Must run immediately after wiki pages are written, before any adversarial review. Note: placeholder URLs in code blocks (e.g., `https://www.youtube.com/playlist?list=PLAYLIST_ID`) are not broken citations — the checker should eventually distinguish these from URLs in Sources sections.

3. **Test suite** — Runs Tier 1 and Tier 2 tests to establish baseline.

## The Principle

LLM reviewers are expensive, slow, and probabilistic. Deterministic tools are cheap, fast, and exhaustive. Run the cheap exhaustive checks first so LLM reviewers can focus on what only they can do: semantic understanding, code-wiki alignment, and judgment calls.

See also: [[concepts/adversarial-review-system]], [[connections/url-rot-and-research-agents]].
