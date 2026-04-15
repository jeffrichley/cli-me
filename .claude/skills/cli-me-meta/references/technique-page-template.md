# Technique Page Template

Every technique page in references/techniques/ must follow this structure.
The three layers (domain knowledge, executable knowledge, provenance) are
mandatory — don't skip any.

---

```markdown
# {{Technique Name}}

## When to Use
{{Describe the scenarios where this technique applies.
Be specific — "product photos for POD" not "when editing images".}}

## Technique
{{Explain the concept. What is this, how does it work, what parameters
matter, what are common mistakes. This is the domain knowledge layer.}}

## CLI Commands
```bash
# {{Description of what this command does}}
uv run scripts/{{name}}_cli.py {{command}} {{flags}}
```

## Under the Hood
{{What does the CLI command actually do? Which software functions does it
call? Link to source-analysis/key-functions.md for details.}}

## Sources
- [{{Source title}}]({{url}})
- Analyzed from: {{Software}} {{version}} (see analyzed-version.md)

## Learned from Usage
{{This section grows over time as agents use the skill.
Format: YYYY-MM-DD: What happened and what was learned.}}
```
