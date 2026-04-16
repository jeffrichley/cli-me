# Skill Template

Use this template when generating a new skill's SKILL.md. Replace all
`{{placeholders}}` with actual values.

---

```markdown
---
name: {{name}}
description: {{description — what it does + when to use it. Include trigger
  phrases like "edit images", "remove background", "batch process". Under 1024
  characters. No XML angle brackets.}}
---

# {{Software Name}} — cli-me skill

CLI-powered interface for {{Software Name}}. This skill wraps the real
{{Software}} executable — it does not reimplement functionality in Python.

## Prerequisites

- {{Software}} must be installed: `{{install command}}`
- Python 3.12+

## CLI Commands

Run commands via:
```bash
uv run scripts/{{name}}_cli.py <command> [options]
```

### Available Commands

{{List each command group and command with a one-line description}}

## Default Behavior

{{Document: default output location, overwrite behavior, auto-detected
settings (device, format), and processing time estimates. Include timeout
guidance for agents — e.g., "Use timeout: 600000 for Bash tool calls" or
"Run in background for long operations."}}

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how something works under the hood, check
`references/source-analysis/`.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Append a timestamped entry to `references/log.md` with what you did and
   what you learned
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
```
