# cli-me Knowledge Base

Two-tier knowledge base for the cli-me skill-building framework.

## Tiers

1. **Process Knowledge** (`knowledge/`) — How to build skills. Patterns, architecture decisions, testing strategies, review techniques. Applies to all future builds.
2. **Tool-Specific Knowledge** (`skill-repo/<name>/references/`) — Gotchas and techniques for a particular tool. Lives in the skill's own directory.

Both tiers are fed by the same hooks: sessions get captured, flushed to daily logs, and compiled into articles. The flush prompt tags each lesson as `[PROCESS]` or `[TOOL:<name>]` so the compiler routes them correctly.

## Quick Start

```bash
cd claude-memory-compiler
uv sync
```

Hooks are configured in `../.claude/settings.json` and activate automatically.

## Key Commands

```bash
uv run python scripts/compile.py                    # compile new daily logs
uv run python scripts/compile.py --all              # force recompile everything
uv run python scripts/query.py "question"            # ask the knowledge base
uv run python scripts/lint.py                        # run health checks
uv run python scripts/lint.py --structural-only      # free structural checks only
```

## Architecture

See [AGENTS.md](AGENTS.md) for the complete technical reference.
