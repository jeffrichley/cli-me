# cli-me: Agent-Native Skills for GUI Software

**Date:** 2026-04-14
**Status:** Draft
**Author:** Jeff Richley + Claude

---

## Problem

CLI-Anything proved the concept — AI agents need CLI interfaces to operate GUI software. But the execution fell short:

- Wrappers are shallow and auto-generated. Many reimplement functionality in Python instead of calling the real software (e.g., the GIMP wrapper uses Pillow internally despite the project's own rules against this).
- Over-engineered packaging (namespace packages, REPL skins, session locking) for what amounts to "call a CLI with the right flags."
- No quality gate. 45+ wrappers with no curation. Quantity over quality.
- SKILL.md files describe commands but don't teach agents *when* or *why* to use them. No workflow intelligence.

## Solution

cli-me reimplements the concept as **native Claude Code skills** with:

- A **meta-skill** that builds high-quality skills by researching source code and web best practices
- A **self-evolving wiki** (Karpathy's LLM Wiki pattern) per skill that grows smarter with every use
- **Typer CLIs** that call the real software — never reimplement
- A **CLI installer** for deploying skills to projects or globally

## Principles

1. **Call the real software, don't reimplement it.** The CLI generates valid inputs and invokes the real application headlessly. If the software isn't installed, fail loudly.
2. **Research the source, don't guess.** The meta-skill clones the actual source code and reads it to understand how to wrap it. This is how you find the real API, not by guessing from the GUI.
3. **Self-evolving knowledge.** Every skill instructs Claude to write back what it learned after each use. The wiki compounds over time.
4. **Concept-to-command mapping.** Wiki pages translate domain knowledge into executable CLI commands at research time. An agent using the skill never sees "click this then that."
5. **Quality over quantity.** Five excellent skills beat 45 mediocre ones.

---

## Repo Structure

```
cli-me/
├── .claude/
│   └── skills/
│       └── cli-me-meta/              # The meta-skill (skill builder)
│           ├── SKILL.md              # How to build cli-me skills
│           ├── scripts/              # Scaffolding, research, validation
│           └── references/           # Templates, patterns, meta-wiki
│
├── skill-repo/
│   ├── registry.json                 # Rich index of all skills
│   ├── gimp/
│   │   ├── SKILL.md                  # Teaches Claude when/why/how
│   │   ├── scripts/
│   │   │   ├── pyproject.toml        # Self-contained — uv run works standalone
│   │   │   └── gimp_cli.py           # Typer CLI driving GIMP headlessly
│   │   └── references/               # LLM Wiki (living knowledge base)
│   │       ├── index.md              # Wiki table of contents
│   │       ├── log.md                # Append-only learning log
│   │       ├── source-analysis/
│   │       │   ├── analyzed-version.md
│   │       │   ├── api-surface.md
│   │       │   ├── cli-interface.md
│   │       │   ├── internal-architecture.md
│   │       │   ├── key-functions.md
│   │       │   └── changelog.md
│   │       ├── techniques/
│   │       │   ├── background-removal.md
│   │       │   └── ...
│   │       └── gotchas.md
│   ├── blender/
│   ├── comfyui/
│   ├── comfyui-vnccs/
│   └── kohya-ss/
│
├── cli/
│   └── cli_me.py                     # Installer CLI (Typer)
│
├── tmp/
│   └── source-analysis/              # Cloned repos for analysis (gitignored)
│
├── pyproject.toml
└── README.md
```

---

## The Meta-Skill

The meta-skill lives at `.claude/skills/cli-me-meta/` and is available when working in the cli-me repo. It drives the entire skill-building process.

### Phase 1: Research

1. **Clone the target software's repo** to `tmp/source-analysis/<name>/`.
2. **Analyze the codebase:**
   - Find CLI entry points, Python bindings, REST APIs, scripting interfaces, headless modes
   - Map GUI actions to underlying API calls
   - Identify the data model and file formats
   - Note the release version (git tag / commit hash)
3. **Research the web:**
   - Best practices and tutorials
   - Common workflows and use cases
   - Known issues and workarounds
4. **Write initial wiki pages** from findings:
   - Source analysis pages with version tracking
   - Technique pages with concept-to-command mapping
   - All entries include source URLs for attribution and troubleshooting

### Phase 2: Scaffold

1. Create `skill-repo/<name>/` with the standard structure
2. Generate SKILL.md with proper frontmatter and trigger phrases
3. Scaffold the Typer CLI in `scripts/`
4. Initialize the wiki with `index.md`, `log.md`, and research pages from Phase 1
5. Add entry to `registry.json`

### Phase 3: Implement

1. Write the Typer CLI that drives the software headlessly
2. Follow the principle: **call the real software, don't reimplement it**
3. Include `detect_version()` in the backend for version-aware behavior
4. Wire up commands that match the workflows identified in research

### Phase 4: Test

1. Verify the CLI works against the real installed software
2. Test that the skill triggers correctly on relevant queries
3. Test that it doesn't trigger on irrelevant queries
4. Document results in the wiki

### Phase 5: Write-back Instruction

Every generated SKILL.md includes a section (at the end) instructing Claude to update the wiki after each use:

```markdown
## After Completing Your Task

Before ending, update the knowledge base in references/:
1. If you discovered a technique that worked well, add or update the relevant
   page in references/techniques/
2. If something failed or had unexpected behavior, document it in
   references/gotchas.md
3. If you found a better approach than what the wiki suggests, update the page
4. Append a timestamped entry to references/log.md with what you did and
   what you learned
5. Update references/index.md if you added new pages
6. Include source URLs for any external knowledge you referenced
```

The meta-skill's own wiki also self-improves — it learns what research strategies work, what scaffold patterns are best, and what pitfalls to warn about.

---

## Wiki Structure (Karpathy LLM Wiki Pattern)

Each skill's `references/` directory is a living knowledge base with three types of content:

### Source Analysis

Written during the meta-skill's research phase. Updated when a new version of the target software is analyzed.

```
references/source-analysis/
├── analyzed-version.md          # Current version, commit hash, analysis date
│                                # History of previous analyses
├── api-surface.md               # Public APIs, bindings, scripting interfaces
├── cli-interface.md             # Headless flags, batch processing, entry points
├── internal-architecture.md     # How the software works internally
├── key-functions.md             # Important functions with source references
└── changelog.md                 # Version deltas: what broke, what's new,
                                 # what's deprecated
```

### Technique Pages

The core knowledge. Each page has three layers:

1. **Domain knowledge** — what the technique is, when to use it, best parameters, common mistakes
2. **Executable knowledge** — the exact CLI commands, what they do under the hood, edge cases
3. **Provenance** — source URLs for attribution, deeper reading, and troubleshooting

```markdown
# Background Removal

## When to Use
- Product photos for POD (t-shirts, mugs)
- Character art cleanup before compositing

## Technique
For high-contrast subjects (text, logos), color-to-alpha is fastest.
For photographic subjects, use threshold selection + mask.
Best radius for POD t-shirt graphics: 1-2px feather to avoid aliasing.

## CLI Commands
\```bash
# Simple color-to-alpha (great for logos on white)
uv run scripts/gimp_cli.py remove-bg --method color-to-alpha --color white --input logo.png --output logo-transparent.png

# Threshold for complex subjects
uv run scripts/gimp_cli.py remove-bg --method threshold --threshold 128 --feather 2 --input photo.png --output clean.png
\```

## Under the Hood
- `color-to-alpha` calls Python-Fu `gimp-drawable-color-balance` → `python-fu-color-to-alpha`
- See: source-analysis/key-functions.md#color-to-alpha

## Sources
- [GIMP docs: Color to Alpha](https://docs.gimp.org/en/gimp-filter-color-to-alpha.html)
- Analyzed from: GIMP 3.0.2 (see analyzed-version.md)

## Learned from Usage
- 2026-04-15: White color-to-alpha leaves faint halo on dark images.
  Fix: pre-desaturate. Added --pre-desaturate flag to CLI.
```

### Operational Files

```
references/
├── index.md     # Table of contents, organized by topic
├── log.md       # Append-only chronological log of learnings
└── gotchas.md   # Known issues, failure modes, workarounds
```

---

## Version Awareness

### In the Wiki

- `analyzed-version.md` records which release was analyzed (tag + commit hash)
- `changelog.md` captures meaningful deltas between versions
- When a new version drops, the meta-skill re-runs source analysis against the new tag, diffs against existing wiki, updates pages in place, and appends to changelog

### In the CLI Backend

Every Typer CLI backend includes a `detect_version()` function:

```python
def detect_version() -> tuple[int, ...]:
    """Detect installed software version."""
    result = subprocess.run(["gimp", "--version"], capture_output=True, text=True)
    # parse and return version tuple
    ...
```

Version-specific behavior uses simple branching:

```python
def apply_filter(name: str, params: dict) -> Result:
    version = detect_version()
    if version >= (3, 0):
        return _apply_filter_v3(name, params)
    else:
        return _apply_filter_v2(name, params)
```

Start with if/else. Extract a protocol/strategy pattern when the branching justifies it.

---

## Installer CLI

A Typer CLI registered as `clime` and `cli-me` in pyproject.toml:

```toml
[project.scripts]
clime = "cli_me:main"
cli-me = "cli_me:main"
```

### Commands

```bash
# Install a skill (copies the full skill folder)
uv run clime install gimp --project /path/to/project
# → copies skill-repo/gimp/ to /path/to/project/.claude/skills/gimp/

uv run clime install gimp --global
# → copies skill-repo/gimp/ to ~/.claude/skills/gimp/

# List available skills
uv run clime list
uv run clime list --category image

# Search skills
uv run clime search "ai training"

# Uninstall
uv run clime uninstall gimp --project /path/to/project

# Show skill info
uv run clime info gimp
```

### Registry

`skill-repo/registry.json` is the index:

```json
{
  "skills": [
    {
      "name": "gimp",
      "description": "Image editing CLI for GIMP",
      "category": "image",
      "tags": ["image-editing", "graphics", "pod", "background-removal"],
      "version": "0.1.0",
      "software_url": "https://www.gimp.org",
      "source_repo": "https://gitlab.gnome.org/GNOME/gimp",
      "dependencies": []
    },
    {
      "name": "comfyui-vnccs",
      "description": "Visual novel character sprite pipeline for ComfyUI",
      "category": "ai-pipeline",
      "tags": ["comfyui", "character-sprites", "visual-novel", "ai-generation"],
      "version": "0.1.0",
      "software_url": "https://github.com/AHEKOT/ComfyUI_VNCCS",
      "source_repo": "https://github.com/AHEKOT/ComfyUI_VNCCS",
      "dependencies": ["comfyui"]
    }
  ]
}
```

---

## Initial Skills

| Skill | Software | Backend Pattern | Primary Use |
|-------|----------|----------------|-------------|
| gimp | GIMP | subprocess (Python-Fu / Script-Fu headless) | Image editing, POD graphic cleanup |
| blender | Blender | subprocess (`blender --background --python`) | 3D modeling, rendering |
| comfyui | ComfyUI | REST API (localhost:8188) | AI image generation |
| comfyui-vnccs | ComfyUI_VNCCS | REST API via ComfyUI (custom nodes) | Consistent character sprites |
| kohya-ss | kohya_ss | subprocess (training scripts) | LoRA model training |

---

## Skill Lifecycle

```
┌─────────────────────────────────────────────────────┐
│ META-SKILL BUILDS THE SKILL                         │
│                                                     │
│  Research → Scaffold → Implement → Test → Publish   │
│  (clone repo,  (create    (Typer   (verify  (add to │
│   read code,    folder,    CLI,     against  registry│
│   search web,   SKILL.md,  call     real     .json)  │
│   write wiki)   init wiki) real     software)        │
│                            software)                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ USER INSTALLS THE SKILL                             │
│                                                     │
│  uv run clime install gimp --project ./my-project   │
│  → copies skill-repo/gimp/ to .claude/skills/gimp/  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ AGENT USES THE SKILL                                │
│                                                     │
│  Claude loads SKILL.md → reads wiki as needed →     │
│  calls Typer CLI → gets results → writes back       │
│  learnings to the wiki                              │
│                                                     │
│  Wiki grows smarter with every use.                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ NEW SOFTWARE VERSION DROPS                          │
│                                                     │
│  Meta-skill re-analyzes → diffs wiki → updates      │
│  pages → appends changelog → CLI gets version-      │
│  aware branches if needed                           │
└─────────────────────────────────────────────────────┘
```

---

## Open Questions

1. **Script invocation from installed skills.** Each skill's `scripts/` directory contains its own `pyproject.toml` declaring Typer as a dependency. This makes each skill self-contained — `uv run scripts/gimp_cli.py <command>` works from the skill directory without any dependency on the cli-me repo. The SKILL.md instructs Claude to run commands from the skill's scripts directory.

---

## What This Is Not

- **Not a REPL framework.** No interactive sessions, no prompt-toolkit, no branded banners. Skills are invoked by Claude, not by humans typing in a terminal.
- **Not a namespace package system.** No setup.py, no PEP 420, no pip install. Skills are folders with markdown and scripts.
- **Not a reimplementation of software.** The Typer CLI calls GIMP, it doesn't become GIMP.
- **Not a junk drawer.** Five high-quality skills that compound knowledge beat 45 shallow wrappers.
