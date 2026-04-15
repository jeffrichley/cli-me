# Wiki Initialization Template

Use this when scaffolding a new skill's references/ directory.

## Files to create

### references/index.md

```markdown
# {{Software Name}} Knowledge Base

## Source Analysis
- [Analyzed Version](source-analysis/analyzed-version.md) — version and analysis metadata
- [API Surface](source-analysis/api-surface.md) — scripting interfaces and bindings
- [CLI Interface](source-analysis/cli-interface.md) — headless modes and flags
- [Internal Architecture](source-analysis/internal-architecture.md) — how the software is structured
- [Key Functions](source-analysis/key-functions.md) — important functions for CLI wrapping
- [Changelog](source-analysis/changelog.md) — version deltas

## Techniques
{{Add links as technique pages are created}}

## Operational
- [Gotchas](gotchas.md) — known issues and workarounds
- [Learning Log](log.md) — chronological record of learnings
```

### references/log.md

```markdown
# Learning Log

Append-only chronological record. Newest entries at the bottom.

---

**{{YYYY-MM-DD}}** — Initial research completed. Analyzed {{Software}} {{version}}.
Created source analysis and technique pages from codebase review and web research.
```

### references/gotchas.md

```markdown
# Gotchas

Known issues, failure modes, and workarounds discovered through research and usage.

{{Add entries as they are discovered}}
```

### references/source-analysis/analyzed-version.md

```markdown
# Analyzed Version

**Current:** {{Software}} {{version}} (commit {{hash}}, analyzed {{YYYY-MM-DD}})

## Analysis History

| Date | Version | Commit | Notes |
|------|---------|--------|-------|
| {{YYYY-MM-DD}} | {{version}} | {{hash}} | Initial analysis |
```

### references/source-analysis/changelog.md

```markdown
# Changelog

Version deltas: what changed in the software's API, CLI, and internals.
Updated when re-analyzing a new version.

{{No entries yet — will be populated on version updates}}
```
