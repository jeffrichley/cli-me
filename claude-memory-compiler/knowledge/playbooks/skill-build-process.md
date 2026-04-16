---
title: Skill Build Process
tags: [process, architecture]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# Skill Build Process

The end-to-end process for building a cli-me skill, incorporating all lessons learned from ffmpeg, yt-dlp, and demucs builds.

## Phase 1: Research

1. Analyze the tool's source repository for features and flags
2. Run the **installed** binary's `--help` and compare against source — only wrap confirmed features (see [[concepts/version-divergence]])
3. Identify all interactive prompts and their suppression flags (see [[connections/interactive-prompts-in-agent-context]])
4. Dispatch [[concepts/parallel-agent-research|parallel research agents]] to produce technique pages
5. Run deterministic URL checker immediately after wiki pages are written (see [[connections/url-rot-and-research-agents]])
6. If wrapping an ML tool, document expected runtimes and set explicit timeout guidance in SKILL.md

## Phase 2: Architecture

1. Split CLI into modules from the start — one file per command group (see [[concepts/thin-wrapper-architecture]])
2. Use thin wrapper pattern: CLI layer parses args, delegates to `commands/` logic layer
3. Identify if the skill needs API keys/config — plan `~/.cli-me/config.toml` entries

## Phase 3: Implementation (per command group)

Follow [[concepts/qa-before-implementation|QA-first order]] for each command group:

1. [ ] Write QA playbook for the group
2. [ ] Write Tier 1 tests (mock subprocess, verify flag construction)
3. [ ] Implement the commands
4. [ ] Run Tier 1 tests — all must pass
5. [ ] Write Tier 2 tests with [[concepts/assertion-depth|deep assertions]]
6. [ ] Run Tier 2 tests — all must pass
7. [ ] Commit the group

Use parallel agents for independent command groups when the module architecture supports it.

## Phase 4: Adversarial Review

1. Run [[concepts/deterministic-before-llm|deterministic checks]] first (link checker, URL checker, test suite)
2. Dispatch all 5 reviewers with [[concepts/fresh-context-for-review|fresh context]] (zero build history)
3. Objective failures enter auto-fix loop (3-strike limit)
4. Judgment calls accumulate for human decision
5. Repeat until clean

See [[concepts/adversarial-review-system]] for the full review protocol.

## Phase 5: Ship

1. Run full test suite (Tier 1 + Tier 2)
2. Generate Tier 3 samples for human review
3. Update documentation
4. Final URL check
5. Ship

## Anti-Patterns

- Implementing all commands before testing any (ffmpeg lesson)
- Using shallow assertions ("file exists") instead of deep property checks
- Reviewing your own code in the same context you wrote it
- Citing research URLs without verification
- Wrapping features from source repo that aren't in the installed release
