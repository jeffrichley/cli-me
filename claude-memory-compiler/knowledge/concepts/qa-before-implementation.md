---
title: QA Before Implementation
tags: [process, testing]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# QA Before Implementation

QA must come before implementation, not after. The ffmpeg build shipped 34 commands before testing any of them against the real binary, resulting in widespread issues that required rework.

## The Problem

When implementation runs ahead of testing, errors compound. Each untested command may rely on assumptions from a previous untested command. By the time QA runs, the fix surface is enormous and interconnected.

## The Rule

For each command group, follow this sequence:

1. Write QA playbook
2. Write Tier 1 tests (command-graph, mocked subprocess)
3. Implement the command
4. Run Tier 1 tests
5. Write Tier 2 tests (integration, real binary)
6. Run Tier 2 tests
7. Commit

This applies per command group, not per entire skill. The unit of work is small enough that QA stays tractable.

## Three-Tier QA Framework

The framework that enforces this discipline has three tiers:

- **Tier 1 (command-graph):** Mocks subprocess, verifies flag construction. Fast, catches syntax and argument errors.
- **Tier 2 (integration):** Uses real binary with deep property assertions. The real quality gate. See [[concepts/assertion-depth]].
- **Tier 3 (manual):** Generates files for human review. Catches what code cannot assert — perceptual quality, visual correctness.

QA lives in `qa/<name>/` and is never shipped with the skill.

## Evidence

The ffmpeg build validated this lesson through pain: all 34 commands were implemented before any Tier 2 testing. The yt-dlp and demucs builds followed QA-first and had significantly fewer rework cycles.

See also: [[concepts/assertion-depth]], [[playbooks/skill-build-process]].
