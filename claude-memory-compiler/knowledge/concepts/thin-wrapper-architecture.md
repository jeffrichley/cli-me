---
title: Thin Wrapper + Logic Layer Architecture
tags: [architecture, process]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# Thin Wrapper + Logic Layer Architecture

CLI commands should parse arguments and delegate to logic functions in a `commands/` module. Logic functions are independently testable without Typer. This separation makes Tier 1 tests cleaner and enables reuse.

## Structure

```
skill-name/
├── cli.py          # Typer app, arg parsing only
├── commands/       # Logic functions, one file per command group
│   ├── convert.py
│   ├── analyze.py
│   └── ...
└── ...
```

## Why This Matters

The ffmpeg build started with a single `ffmpeg_cli.py` at 1000+ lines containing all 34 commands. This made testing difficult, navigation painful, and parallel implementation impossible (merge conflicts on a single file).

The split-by-group architecture was adopted for subsequent builds and enables:

- **Parallel implementation:** Multiple agents work on different command groups simultaneously without conflicts (see [[concepts/parallel-agent-research]])
- **Targeted testing:** Tier 1 tests import logic functions directly, no Typer CLI overhead
- **Clean boundaries:** Each module has a clear responsibility scope

## Scope Boundaries

cli-me wraps existing tools. It does not:

- Manage custom data (voice profiles, embeddings, LoRA storage) — that's orchestration, not wrapping
- Provide framework-level configuration — though skills needing API keys/config need a `~/.cli-me/config.toml` with global defaults and per-skill overrides

## CLI Tool Advantage

CLI tools (like yt-dlp) are faster to wrap than GUI applications. The thin wrapper pattern works identically for both, but the research and flag-mapping phase is shorter when the source tool already has a CLI interface.

See also: [[concepts/qa-before-implementation]], [[playbooks/skill-build-process]].
