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
6. **Adversarial review at every phase.** Fresh agents (never the creator) review
   every artifact. Objective failures auto-fix with a 3-strike limit. Judgment calls
   accumulate for human decision at phase boundaries. See
   `references/adversarial-reviewers/protocol.md` for the Review Result
   Handling Protocol and individual reviewer files under
   `references/adversarial-reviewers/` for each reviewer prompt.
7. **Thin wrappers, testable logic.** CLI commands parse args and delegate to logic
   functions in `commands/`. Logic functions are independently testable without Typer.

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

### 1d. REVIEW: Wiki Technique Pages (Adversarial)

Dispatch a **fresh reviewer agent** (NOT the research agent) using the
"Reviewer 1: Wiki Technique Page Reviewer" prompt from
`references/adversarial-reviewers/r1-wiki-technique.md`.

The reviewer checks: command accuracy, URL verification (fetch every URL),
completeness, accuracy of claims, and creative edge case hunting.

Fix all findings before proceeding. Re-review if significant changes made.

### 1e. Initialize the wiki

Create the wiki operational files:

- `references/index.md` — table of contents linking to all pages created above
- `references/log.md` — first entry: "YYYY-MM-DD: Initial research completed.
  Analyzed <software> <version>. Created source analysis and technique pages."
- `references/gotchas.md` — any issues or warnings discovered during research

## Phase 2: Scaffold

Create the skill folder structure. **The CLI is a package, not a single file.**
Split commands into modules by group from the start — one file per command group
keeps files focused and enables parallel agent work:

```
skill-repo/<name>/
├── SKILL.md
├── scripts/
│   ├── pyproject.toml        # Self-contained — declares Typer dep so uv run works
│   └── <name>_cli/
│       ├── __init__.py       # Exports `app`
│       ├── __main__.py       # `python -m <name>_cli` support
│       ├── backend.py        # find_executable, detect_version, run helpers
│       ├── convert.py        # Thin CLI wrapper — parses args, delegates
│       ├── extract.py        # Thin CLI wrapper
│       └── commands/         # Logic layer — independently testable
│           ├── __init__.py
│           ├── convert_format.py   # One function per command
│           ├── extract_clip.py
│           └── ...
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

### Scaffold Entry Point

Create a shim script at `scripts/<name>_cli.py` so `uv run` can invoke the CLI
directly. Package directories cannot be invoked with `uv run <dir>` — a top-level
script is required:

```python
"""Entry point for uv run <name>_cli.py"""
from <name>_cli import app

if __name__ == "__main__":
    app()
```

**Verify the scaffold works before proceeding:**
```bash
cd skill-repo/<name>/scripts
uv run <name>_cli.py --help
```
If this fails, fix the entry point before moving to Phase 3.

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

### REVIEW: Scaffold (Adversarial)

Dispatch a **fresh reviewer agent** using the "Reviewer 2: Scaffold Reviewer"
prompt from `references/adversarial-reviewers/r2-scaffold.md`.

The reviewer checks: frontmatter validity, body clarity, reproducibility,
registry consistency, directory structure, and trigger conflict hunting.

Fix all findings before proceeding.

## Phase 3: QA-First Implementation

**CRITICAL: Write tests BEFORE implementing commands. Test each command as you
build it. Never implement all commands and test later.**

**This applies to ALL code changes, not just initial implementation.** When
adding a new parameter to an existing command (e.g., adding `--no-overwrites`
during a fix round), write the test FIRST. The test-first discipline applies
equally to new features and to fixes.

### 3a. Write the QA playbook

Create `qa/<name>/playbook.md` FIRST — before any implementation. Document:
- What each command should do
- Input required, expected output, verification method
- Manual verification steps for visual/audio quality
- Known edge cases and gotchas

### 3b. Write the backend module

Create `scripts/<name>_cli/backend.py` with:

```python
import subprocess
import shutil
import typer

def find_executable(name: str) -> str:
    """Find the software executable or exit with install instructions."""
    path = shutil.which(name)
    if path is None:
        typer.echo(f"ERROR: {name} not found. Install with: <instructions>", err=True)
        raise typer.Exit(code=1)
    return path

def detect_version() -> tuple[int, ...]:
    """Detect installed software version."""
    ...

def run_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a software command and return the result."""
    ...
```

### 3b.1 Interactive Prompt Suppression

Agent contexts have no stdin. If the wrapped software has interactive prompts
(overwrite confirmation, yes/no questions, license acceptance), the CLI will
hang silently with no error.

**Every `build_args` function MUST include a flag that suppresses interactive
prompts by default.** Research what flag the wrapped software uses (e.g., `-y`,
`--force`, `--yes`, `--force-overwrites`, `--batch`, `--non-interactive`).

Add a `no_overwrites: bool = False` parameter (or equivalent) so agents can
opt into the safer behavior, but the default MUST be non-interactive. Document
this default in the skill's SKILL.md and gotchas.md.

### 3c. For EACH command group, follow this cycle:

**DO NOT skip steps. DO NOT batch implement all commands then test.**

1. **Write Tier 1 test** (`qa/<name>/test_commands.py`):
   - Mock subprocess.run and shutil.which
   - Assert the command builds the correct argument list
   - Mark with `@pytest.mark.command_graph`

2. **Run Tier 1 test — verify it fails**

3. **Implement the command** in its own module (`scripts/<name>_cli/<group>.py`)

4. **Run Tier 1 test — verify it passes**

5. **Write Tier 2 test** (`qa/<name>/test_integration.py`):
   - Use synthetic fixtures from `qa/conftest.py`
   - Run real command against real software
   - **Deep assertions**: exact dimensions, codecs, pixel formats, magic bytes,
     duration precision, file size comparison, stream presence/absence.
   - "File exists and is nonzero" is NEVER sufficient.
   - Mark with `@pytest.mark.integration`

6. **Run Tier 2 test — verify it passes against real software**
   - If it fails, fix the command and re-run
   - If the software is not installed, the test skips gracefully

7. **REVIEW: Code-Wiki Alignment (Adversarial)**
   Dispatch a **fresh reviewer agent** using "Reviewer 3: Code-Wiki Alignment
   Reviewer" from `references/adversarial-reviewers/r3-code-wiki.md`. The reviewer
   cross-references wiki commands against the code, checks thin wrapper
   compliance, error handling, and hunts for silent failures.
   Fix all findings before committing.

8. **REVIEW: Test Quality (Adversarial)**
   Dispatch a **fresh reviewer agent** using "Reviewer 4: Test Quality
   Reviewer" from `references/adversarial-reviewers/r4-test-quality.md`. The reviewer
   performs mutation analysis on the tests, checks assertion depth, finds
   coverage gaps, and identifies bugs that would pass all tests.
   Fix all findings before committing.

9. **Commit the command + both tests together**

10. **Repeat for the next command group**

### 3d. REVIEW: Wiki Execution Verification (Adversarial)

Dispatch a **fresh reviewer agent** using "Reviewer 5: Wiki Execution Reviewer"
from `references/adversarial-reviewers/r5-wiki-execution.md`.

This reviewer RUNS every command documented in every technique page against
the real software, verifies outputs, fetches every source URL, and tests
adversarial inputs (spaces in filenames, edge durations, unusual resolutions).

Fix all findings. Update wiki pages with corrected commands. Re-run failing
commands until they pass.

### 3d.1 Deterministic URL Check

Run the URL checker script against the skill's wiki pages:

```bash
uv run qa/check_urls.py <name>
```

This deterministically fetches EVERY URL in every technique page and reports
HTTP status codes. No LLM judgment — pure HTTP status. Fix all dead URLs
(404, 403, 410, 5xx, timeout) before proceeding.

This catches URL rot that adversarial reviewers miss because they spot-check.
The script checks ALL URLs. Run it after every round of URL replacements
until the output is clean.

### 3d.2 Deterministic Link Check

Run the link/orphan checker against the skill's wiki pages:

```bash
uv run qa/check_links.py <name>
```

This checks that all relative markdown links resolve to existing files and
that no `.md` files are orphaned (unreferenced by any other `.md` file).
An orphaned file is invisible to agents — they'll never discover it.
Fix all broken links and investigate orphan files before proceeding.

### 3e. Write Tier 3 manual tests

Create `qa/<name>/test_manual.py` — tests that generate output files and print
paths + instructions for human review. Mark with `@pytest.mark.manual`.

Cover anything that can't be asserted programmatically:
- Visual quality (GIFs, resized images, cropped video)
- Audio quality (normalization, denoising, ducking)
- Subtitle visibility and positioning
- Watermark placement and opacity
- Transition smoothness (fades, speed changes)

### 3f. Version-aware branching (when needed)

Use simple branching in the backend module:

```python
version = detect_version()
if version >= (3, 0):
    # new approach
else:
    # legacy approach
```

Extract a protocol/strategy pattern only when branching justifies it.

## Phase 4: Final Verification

1. Run full Tier 1: `uv run pytest qa/<name>/test_commands.py -v`
2. Run full Tier 2: `uv run pytest qa/<name>/test_integration.py -v -m integration`
3. Run Tier 3: `uv run pytest qa/<name>/test_manual.py -v -m manual -s`
4. Have a human review Tier 3 outputs
5. Fix any failures found
6. Document test results in `references/log.md`

## Phase 5: Write-back Instruction

Append the standard write-back section to the generated SKILL.md. Read the exact
text from `references/write-back-instructions.md` and append it verbatim.

## After You (the Meta-Skill) Complete a Build

Update your own wiki at `references/meta-wiki/`:
1. Append to `references/meta-wiki/log.md` what you learned about building this skill
2. If you discovered a better research strategy, pattern, or pitfall, update the
   relevant reference file
3. Update `references/meta-wiki/index.md` if you added new pages
