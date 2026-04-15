---
name: cli-me-meta
description: Build high-quality Claude Code skills that wrap GUI software. Use when
  asked to "build a skill for", "wrap", "create a CLI for", or "make a skill" for
  any desktop application. Drives a multi-phase process of source code research, web
  research, wiki creation, CLI scaffolding, and testing.
---

# cli-me Meta-Skill: Build Agent-Native Skills for GUI Software

You are building a cli-me skill — a Claude Code skill that wraps a GUI application
with a Typer CLI so agents can operate it headlessly. Every skill you build must
follow the principles and phases below.

## Principles

1. **Call the real software, don't reimplement it.** Your Typer CLI generates valid
   inputs and invokes the real application via subprocess or REST API. If the software
   isn't installed, fail loudly with install instructions.
2. **Research the source, don't guess.** Clone the software's repo and read the actual
   code to find the API surface, scripting interfaces, and headless modes.
3. **Concept-to-command mapping.** Wiki pages translate domain knowledge into executable
   CLI commands. An agent using the skill should never see "click this then that."
4. **Self-evolving knowledge.** Every generated skill instructs agents to write back
   what they learned to the wiki after each use.
5. **Attribution always.** Every wiki page links back to source URLs.

## Phase 1: Research

### 1a. Clone the source

Clone the target software's repository to `tmp/source-analysis/<name>/`:

```bash
git clone <repo-url> tmp/source-analysis/<name>
```

If the repo is very large, use `--depth 1` for a shallow clone.

### 1b. Analyze the codebase

Read the cloned source to answer these questions. Write findings to wiki pages
as you go (don't wait until the end):

- **API surface** → `references/source-analysis/api-surface.md`
  - What scripting interfaces exist? (Python bindings, Script-Fu, REST API, CLI flags)
  - What are the main entry points for headless/batch operation?
  - What functions correspond to common GUI actions?

- **CLI interface** → `references/source-analysis/cli-interface.md`
  - What command-line flags does the software support?
  - What headless/batch modes are available?
  - How do you invoke it without a display?

- **Internal architecture** → `references/source-analysis/internal-architecture.md`
  - How is the software structured? (plugins, modules, node graph, etc.)
  - Where does the core logic live vs. the GUI layer?

- **Key functions** → `references/source-analysis/key-functions.md`
  - Document important functions with file paths and line numbers
  - Focus on functions the Typer CLI will need to invoke

- **Version** → `references/source-analysis/analyzed-version.md`
  - Record the git tag, commit hash, and date analyzed
  - Note the version string from the software's own metadata

### 1c. Research the web

Search for:
- Official documentation for headless/scripting usage
- Tutorials and best practices for batch processing
- Common workflows and use cases
- Known issues and workarounds
- Community scripts and automation examples

Write findings as technique pages in `references/techniques/`. Every page must
include source URLs.

### 1d. Initialize the wiki

Create the wiki operational files:

- `references/index.md` — table of contents linking to all pages created above
- `references/log.md` — first entry: "YYYY-MM-DD: Initial research completed.
  Analyzed <software> <version>. Created source analysis and technique pages."
- `references/gotchas.md` — any issues or warnings discovered during research

## Phase 2: Scaffold

Create the skill folder structure:

```
skill-repo/<name>/
├── SKILL.md
├── scripts/
│   ├── pyproject.toml        # Self-contained — declares Typer dep so uv run works
│   └── <name>_cli.py
└── references/
    ├── index.md
    ├── log.md
    ├── gotchas.md
    ├── source-analysis/
    │   ├── analyzed-version.md
    │   ├── api-surface.md
    │   ├── cli-interface.md
    │   ├── internal-architecture.md
    │   ├── key-functions.md
    │   └── changelog.md
    └── techniques/
        └── (pages from Phase 1)
```

Generate the SKILL.md using the template at `references/skill-template.md`.

Generate the scripts/pyproject.toml so the CLI is self-contained:

```toml
[project]
name = "<name>-cli"
version = "0.1.0"
description = "Agent-native CLI for <Software Name>"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
]

[project.scripts]
<name>-cli = "<name>_cli:app"
```

Add an entry to `skill-repo/registry.json` using the Registry class or by
appending to the JSON directly:

```json
{
  "name": "<name>",
  "description": "<one-line description>",
  "category": "<category>",
  "tags": ["<tag1>", "<tag2>"],
  "version": "0.1.0",
  "software_url": "<software homepage>",
  "source_repo": "<git clone url>",
  "dependencies": []
}
```

## Phase 3: Implement

Create `scripts/pyproject.toml` so the CLI is self-contained and `uv run` works
without the cli-me repo:

```toml
[project]
name = "<name>-cli"
version = "0.1.0"
description = "Agent-native CLI for <Software Name>"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15.0",
]

[project.scripts]
<name>-cli = "<name>_cli:app"
```

Write the Typer CLI at `scripts/<name>_cli.py`. Follow the template at
`references/typer-cli-template.md`.

Every CLI must include:

```python
import subprocess
import shutil
import typer

app = typer.Typer(help="<name> CLI — agent-native interface for <Software>")


def detect_version() -> tuple[int, ...]:
    """Detect installed software version."""
    path = shutil.which("<executable>")
    if path is None:
        typer.echo(
            "ERROR: <Software> not found. Install with: <install instructions>",
            err=True,
        )
        raise typer.Exit(code=1)
    result = subprocess.run(
        [path, "--version"], capture_output=True, text=True
    )
    # Parse version from output
    ...


def find_executable() -> str:
    """Find the software executable or exit with install instructions."""
    path = shutil.which("<executable>")
    if path is None:
        typer.echo(
            "ERROR: <Software> not found. Install with: <install instructions>",
            err=True,
        )
        raise typer.Exit(code=1)
    return path
```

Commands should map to the workflows and techniques documented in the wiki.
Use version-aware branching where needed:

```python
version = detect_version()
if version >= (3, 0):
    # new approach
else:
    # legacy approach
```

## Phase 4: Test

### 4a. Generate QA Playbook and Tests

Create the QA suite in `qa/<name>/` (NOT inside the skill folder — QA is never
shipped to users):

1. **`qa/<name>/playbook.md`** — document what to test for each command:
   - Test scenario, input required, expected output, verification method
   - Manual verification steps for visual/audio quality
   - Known edge cases and gotchas

2. **`qa/<name>/test_commands.py`** — Tier 1 command-graph tests:
   - Mock `subprocess.run` and `shutil.which`
   - Invoke each command via CliRunner
   - Assert the correct ffmpeg/software args are constructed
   - No real binary needed — runs everywhere
   - Mark with `@pytest.mark.command_graph`

3. **`qa/<name>/test_integration.py`** — Tier 2 integration tests:
   - Use synthetic fixtures from `qa/conftest.py` (test_video, test_audio, etc.)
   - Run real commands against real software
   - Verify outputs: file exists, correct format (ffprobe), expected properties
   - Mark with `@pytest.mark.integration`
   - Skip gracefully if software not installed

### 4b. Run Tests

1. Run Tier 1: `uv run pytest qa/<name>/test_commands.py -v`
2. Run Tier 2: `uv run pytest qa/<name>/test_integration.py -v -m integration`
3. Fix any failures found
4. Document test results in `references/log.md`

## Phase 5: Write-back Instruction

Append the standard write-back section to the generated SKILL.md. Read the exact
text from `references/write-back-instructions.md` and append it verbatim.

## After You (the Meta-Skill) Complete a Build

Update your own wiki at `references/meta-wiki/`:
1. Append to `references/meta-wiki/log.md` what you learned about building this skill
2. If you discovered a better research strategy, pattern, or pitfall, update the
   relevant reference file
3. Update `references/meta-wiki/index.md` if you added new pages
