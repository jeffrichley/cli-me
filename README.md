# cli-me

Agent-native skills for GUI software. Build, install, and evolve Claude Code
skills that wrap desktop applications with Typer CLIs.

## What is this?

cli-me is a framework for creating Claude Code skills that let AI agents operate
GUI software headlessly. Each skill includes:

- **SKILL.md** — teaches Claude when and how to use the software
- **scripts/** — a Typer CLI that calls the real software (never reimplements it)
- **references/** — a self-evolving wiki that grows smarter with every use

## Quick Start

```bash
# List available skills
uv run clime list

# Install a skill to your project
uv run clime install gimp --project .

# Install globally
uv run clime install gimp --global

# Search for skills
uv run clime search "image editing"

# Get skill details
uv run clime info gimp
```

## Building Skills

The meta-skill at `.claude/skills/cli-me-meta/` guides Claude through building
new skills. In a Claude Code session within this repo:

> "Build me a cli-me skill for GIMP"

The meta-skill drives a multi-phase process: research the source code, search
for best practices, build the wiki, scaffold the CLI, test it, and publish it
to the skill-repo.

## Project Structure

```
cli-me/
├── .claude/skills/cli-me-meta/  # The skill builder
├── skill-repo/                  # Published skills
├── cli_me/                      # Installer CLI (clime)
└── tests/
```

## Design

See [docs/superpowers/specs/2026-04-14-cli-me-design.md](docs/superpowers/specs/2026-04-14-cli-me-design.md)
