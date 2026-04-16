---
title: Interactive Prompts in Agent Context
tags: [process, tooling, agent-patterns]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# Interactive Prompts in Agent Context

This connection links **CLI tool wrapping** with **agent execution environments**: any tool that has an interactive prompt will silently hang when run by an agent, because agent contexts have no stdin.

## The Pattern

CLI tools often prompt for confirmation before destructive actions (overwriting files, deleting data). In a human terminal, this is a safety feature. In an agent context, it's a silent hang — the process waits forever for input that will never come.

## Known Instances

| Tool | Interactive Prompt | Suppression Flag |
|------|-------------------|-----------------|
| ffmpeg | "File already exists. Overwrite? [y/N]" | `-y` |
| yt-dlp | Overwrite confirmation | `--force-overwrites` or `--no-overwrites` |

The ffmpeg `-y` flag issue was missed through the entire build process and two rounds of adversarial review — only caught in Round 3 by R2 (CLI behavior reviewer). This demonstrates both the subtlety of the bug and the value of [[concepts/adversarial-review-system|adversarial review]].

## The Rule

Every CLI skill that wraps a tool with interactive prompts must suppress them. During the research phase, identify all interactive prompts in the tool and document the suppression flags. During implementation, ensure every command that could trigger a prompt includes the appropriate flag.

## Timeout Connection

Related but distinct: ML tools like demucs take minutes per invocation. Without explicit timeout guidance in SKILL.md, agents use default 2-minute Bash timeouts and kill processes mid-run. This isn't an interactive prompt issue — it's a duration issue — but both stem from the same root cause: agent execution environments have different constraints than human terminals.

See also: [[concepts/assertion-depth]], [[concepts/thin-wrapper-architecture]].
