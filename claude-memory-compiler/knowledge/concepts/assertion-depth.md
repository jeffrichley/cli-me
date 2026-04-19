---
title: Assertion Depth — "Runs" Is Not "Works"
tags: [process, testing]
sources: [daily/2026-04-15-seed.md, daily/2026-04-18.md]
created: 2026-04-16
updated: 2026-04-18
---

# Assertion Depth

There are four levels of verification, each catching bugs the previous level misses. All four are needed for quality.

## The Levels

1. **Runs without errors** — proves syntax. The command executes and returns exit code 0.
2. **Runs with shallow assertions** — proves existence. Output file exists and is nonzero.
3. **Runs with deep assertions** — proves correctness. Output has exact dimensions, pixel formats, codec profiles, sample rates, duration precision, stream presence/absence.
4. **Runs with human review** — proves quality. A human evaluates perceptual output.

## The "File Exists" Anti-Pattern

The ffmpeg build's first Tier 2 tests only checked if output existed and was nonzero. This was pushed back twice before the tests included real assertions: exact dimensions, magic bytes, file size comparison, loudness measurements, codec verification.

"File exists" is never a sufficient assertion.

## Conditional Assertion Trap

A particularly dangerous variant: assertions that are conditional on prerequisite checks. The ffmpeg normalize test had its loudness assertion inside `if json_start >= 0` — if JSON parsing failed, the test silently passed with zero loudness verification.

**Rule:** Always assert that prerequisite conditions are met. Never make the real assertion conditional on a parsing or extraction step succeeding. If the prerequisite fails, the test must fail.

## Deep Assertion Examples

| Domain | Shallow | Deep |
|--------|---------|------|
| Video | File exists | Exact resolution, pixel format, codec profile, level |
| Audio | File > 0 bytes | Sample rate, bitrate, loudness (LUFS), channel count |
| Image | File exists | Dimensions, color space, magic bytes |
| Download | File exists | Format, expected metadata, file size in expected range |

## Synthetic Fixture Trap

A related failure mode occurs at a different layer: the assertions are deep and correct, but the test fixture guarantees they never execute. Synthetic fixtures (sine tones, blank images) can produce legitimately empty results, causing assertion loops to iterate zero times. See [[concepts/synthetic-fixture-trap]] for the full pattern.

See also: [[concepts/qa-before-implementation]], [[connections/interactive-prompts-in-agent-context]], [[concepts/synthetic-fixture-trap]].
