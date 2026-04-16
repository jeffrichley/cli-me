---
title: Article Format Templates
tags: [meta, process]
sources: [AGENTS.md]
created: 2026-04-16
updated: 2026-04-16
---

# Article Format Templates

Standard templates for each article type in the cli-me knowledge base.

## Concept Article

```yaml
---
title: Concept Name
tags: [process, architecture, testing, review, research, tooling, agent-patterns, meta]
sources: [daily/YYYY-MM-DD-*.md, https://example.com]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Body uses encyclopedia voice. State the concept, explain why it matters, give examples from actual builds, and link to related articles via `[[wikilinks]]`.

## Connection Article

```yaml
---
title: Connection Between X and Y
tags: [same as above]
sources: [daily/YYYY-MM-DD-*.md]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Body uses analytical voice. State the two or more concepts being connected, explain the relationship, and describe the implications. Must link to all connected concept articles.

## Playbook Article

```yaml
---
title: How to Do X
tags: [same as above]
sources: [daily/YYYY-MM-DD-*.md]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Body uses imperative voice with numbered steps and checklists. Each step should be actionable. Include prerequisites, common pitfalls, and links to relevant concepts.

## QA Article

```yaml
---
title: Q: Question Text
tags: [same as above]
sources: [daily/YYYY-MM-DD-*.md]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Body uses synthesis voice. Restate the question, provide the answer with evidence, and link to supporting concepts.

## Conventions

- **Frontmatter** is required on every article
- **Tags** must come from the standard set: `process`, `architecture`, `testing`, `review`, `research`, `tooling`, `agent-patterns`, `meta`
- **Sources** must reference daily log files or external URLs
- **Wikilinks** use `[[path/slug]]` format without `.md` extension
- Every article must link to at least 2 other articles

See also: [[playbooks/skill-build-process]], the index at `knowledge/index.md`.
