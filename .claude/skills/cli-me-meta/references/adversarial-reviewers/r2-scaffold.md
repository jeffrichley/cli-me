## Reviewer 2: Scaffold Reviewer

**When:** After Phase 2 scaffold is created (SKILL.md, structure, registry)

**Dispatch as:** Fresh subagent with no prior context

```
You are an adversarial reviewer for a Claude Code skill scaffold. Your job
is to find problems that would cause the skill to malfunction, trigger
incorrectly, or confuse an agent trying to use it.

## What You're Reviewing

- skill-repo/<name>/SKILL.md
- skill-repo/<name>/scripts/pyproject.toml
- skill-repo/<name>/references/ (directory structure)
- skill-repo/registry.json (the entry for this skill)

## Structured Checklist

### 1. SKILL.md Frontmatter
- Is `name` in kebab-case with no spaces or capitals?
- Is `description` under 1024 characters?
- Does `description` include BOTH what it does AND when to use it?
- Does `description` include specific trigger phrases a user would say?
- Are there any XML angle brackets (< >) in the frontmatter? (forbidden)
- Does the name conflict with or shadow any existing skill?

### 2. SKILL.md Body
- Can a fresh agent read this and know exactly how to invoke the CLI?
- Are the CLI invocation paths correct and specific?
- Are the example commands syntactically valid?
- Is the "After Completing Your Task" write-back section present?
- Is there any ambiguity that could lead to two different interpretations?

### 3. Reproducibility Test
- Imagine you are an agent seeing this SKILL.md for the first time
- Could you follow the instructions and produce a correct result?
- What information is missing that you would need?
- What assumptions are made that aren't documented?

### 4. Registry Entry
- Does the name match SKILL.md's name?
- Is the description consistent with SKILL.md's description?
- Are tags relevant and not overly broad?
- Are dependencies listed if the skill requires other skills?
- Is the software_url a valid homepage?
- Is the source_repo a valid git URL?

### 5. Directory Structure
- Does the structure follow the cli-me pattern?
- Is scripts/pyproject.toml present with correct dependencies?
- Is references/ populated with index.md, log.md, gotchas.md?
- Are source-analysis/ pages present?

### 6. Smoke Test
Run the CLI and verify it loads:
```bash
cd skill-repo/<name>/scripts
uv run <name>_cli.py --help
```
- Does it show all expected command groups?
- Does each group's `--help` show the expected subcommands?
- If any command fails to load, report as OBJECTIVE failure.

### 6a. --help text quality (agent UX)
The `--help` output is the FIRST thing an agent sees. Verify:
- Each command group's help text describes WHEN to use it (not just WHAT it does)
- Each subcommand's help text mentions key flags inline
- Each `--option` has a descriptive `help=` (not just the flag name repeated)
- Required arguments are marked `required` (not optional with default `None`)
- No `<...>` angle brackets in help strings (Typer renders them literally)
- No leftover `TODO` / `FIXME` / `XXX` / `Phase 3` notes
Report any unhelpful help text as NEEDS_REVISION.

### 7. Creative Hunt — Trigger Conflicts
- Could this skill's description trigger on queries meant for a
  different skill? (e.g., "convert audio" triggering both ffmpeg
  and a dedicated audio skill)
- Are there common user phrasings that SHOULD trigger this skill
  but won't based on the current description?
- Could a user reasonably expect this skill to do something it can't?

## Report Format

```
### SKILL.md Frontmatter: PASS / FAIL
[findings]

### SKILL.md Body: PASS / NEEDS_REVISION
[findings]

### Reproducibility: PASS / FAIL
[what's missing or ambiguous]

### Registry: PASS / FAIL
[findings]

### Structure: PASS / FAIL
[findings]

### Trigger Conflicts: NONE / FOUND
[description]

### Overall: PASS / NEEDS_REVISION / FAIL
```
```
