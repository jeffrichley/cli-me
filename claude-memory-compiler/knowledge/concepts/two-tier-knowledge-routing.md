---
title: Two-Tier Knowledge Routing
tags: [architecture, process, meta]
sources: [daily/2026-04-16.md]
created: 2026-04-18
updated: 2026-04-18
---

# Two-Tier Knowledge Routing

Knowledge produced during skill builds falls into two distinct tiers with different storage locations and access patterns. Routing knowledge to the wrong tier breaks either cross-skill learning or runtime agent lookup.

## The Two Tiers

**Tier 1 — Process Knowledge** lives in the memory compiler wiki (`knowledge/`). This is cross-cutting knowledge about *how to build skills*: patterns, architecture decisions, pitfalls, review techniques. It applies to every future skill build regardless of which tool is being wrapped.

Examples: "QA must come before implementation," "thin wrapper + logic layer architecture," "fresh context is non-negotiable for adversarial reviews."

**Tier 2 — Tool-Specific Knowledge** lives in each skill's `skill-repo/<name>/references/` directory. This is knowledge about *a particular tool*: flags, gotchas, codec behavior, format quirks. Agents access these files at skill runtime to answer user questions.

Examples: "ffmpeg's `-y` flag prevents interactive hangs," "demucs GPU detection must probe the tool's Python," "yt-dlp `--force-overwrites` is the equivalent of ffmpeg's `-y`."

## The Routing Rule

When extracting knowledge from a build session:

- **Process insights** (how to build, test, review, architect) → `knowledge/` wiki
- **Tool-specific discoveries** (flags, formats, runtime behavior) → `skill-repo/<tool>/references/`

## Why Routing Matters

Moving tool-specific content to the meta-wiki would break agent lookup at runtime — agents serving a skill read from that skill's `references/` directory, not from the compiler wiki. Conversely, leaving process insights buried in a single skill's references means other skill builds never benefit from them.

## Cross-Cutting Tool Lessons

Some tool-specific discoveries reveal process patterns. The `-y` flag issue in ffmpeg is a tool-specific fact, but the *pattern* — "interactive prompts silently hang agents" — is a process insight. Both get captured: the process pattern in `knowledge/` as [[connections/interactive-prompts-in-agent-context]], and the tool-specific flag in the skill's references.

## Validation

This routing was validated during the memory compiler installation. The question arose whether per-skill content (ffmpeg/demucs/yt-dlp references) should be migrated to the meta-wiki. The answer was no: each project keeps its own independent installation, and Tier 2 content stays with the skill that uses it.

See also: [[concepts/deterministic-before-llm]], [[playbooks/skill-build-process]].
