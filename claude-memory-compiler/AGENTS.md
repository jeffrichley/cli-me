# AGENTS.md - cli-me Knowledge Base

> Based on [Karpathy's LLM Knowledge Base](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) architecture.

**You are an active knowledge manager.** When you research, discover, evaluate, or build — write what you learn directly into the knowledge base. Don't wait for hooks.

## Two-Tier Wiki Architecture

cli-me has two distinct types of knowledge that get captured:

### Tier 1: Process Knowledge (Meta)

`claude-memory-compiler/knowledge/` is the wiki for **how to build skills** — process patterns, architecture decisions, pitfalls, lessons learned across all skill builds. This is cross-cutting knowledge that applies to every future skill.

Examples: "QA must come before implementation", "thin wrapper + logic layer architecture", "fresh context is non-negotiable for adversarial reviews", "conditional assertions are false-confidence traps".

### Tier 2: Tool-Specific Knowledge

Each skill's `skill-repo/<name>/references/` directory holds **tool-specific knowledge** — gotchas, techniques, learnings from usage of that particular tool (ffmpeg, demucs, yt-dlp, etc.).

Examples: "ffmpeg's `-y` flag prevents interactive hangs", "demucs GPU detection must probe the tool's Python", "yt-dlp `--force-overwrites` is the equivalent of ffmpeg's `-y`".

### Routing Rule

When the flush agent extracts knowledge from a session:
- **Process insights** (how to build skills, test patterns, review techniques, architecture decisions) → `knowledge/` wiki (this directory)
- **Tool-specific discoveries** (flags, gotchas, techniques for a specific tool) → noted in daily log with a tag indicating which skill it belongs to, so the compiler can route it

**Never create documentation, references, or templates outside of `knowledge/`.** Tool-specific knowledge is tagged for later integration into `skill-repo/<name>/references/` but the daily logs and compilation all flow through this wiki.

## Knowledge Base Structure

```
knowledge/
├── index.md              # Master catalog — read FIRST, update on every change
├── log.md                # Append-only build log — append on every change
├── concepts/             # Facts, patterns, decisions, research
├── connections/          # Cross-cutting insights linking 2+ concepts
├── playbooks/            # Operational procedures (how cli-me builds skills)
└── qa/                   # Filed query answers
```

Also: `daily/` holds immutable conversation logs written by hooks.

## How to Work

### Writing knowledge

1. Check `knowledge/index.md` — does an article already exist?
2. If yes: READ it, UPDATE with new information, add source
3. If no: CREATE a new article in the right directory
4. UPDATE `knowledge/index.md`
5. APPEND to `knowledge/log.md`

**Write when you:** discover a process pattern, learn a gotcha during a build, make an architecture decision, improve a review technique, notice a cross-skill pattern, learn something about agent coordination.

**Don't write when:** information is trivial, it's just a conversation artifact, or it would duplicate an existing article (update instead).

### Reading knowledge

Read `knowledge/index.md` first. Pick relevant articles. Read them in full. Cite with `[[wikilinks]]`.

### Article types

| Directory | Contains | Voice |
|-----------|----------|-------|
| `concepts/` | Facts, research, decisions, build learnings | Encyclopedia |
| `connections/` | Insights linking 2+ concepts | Analytical |
| `playbooks/` | Repeatable procedures (research, build, test, review, ship) | Imperative, checklists |
| `qa/` | Filed answers to questions | Synthesis |

For full article format templates, read [[concepts/article-formats]].

## Two Input Streams

1. **You** (active) — write articles directly as you work
2. **Hooks** (passive) — capture conversations into `daily/`, compiled on schedule

For hook and script details, read [[concepts/hooks-and-scripts]].

## Conventions

- **Wikilinks:** `[[path/to/article]]` without `.md` extension
- **Writing style:** Encyclopedia for concepts, imperative for playbooks
- **Dates:** ISO 8601
- **File naming:** lowercase, hyphens for spaces
- **Frontmatter:** Every article needs: title, tags, sources, created, updated
- **Sources:** Daily logs, external URLs, or both
- **Tags:** `process`, `architecture`, `testing`, `review`, `research`, `tooling`, `agent-patterns`, `meta`

## Lint Checks

Seven checks run periodically: broken links, orphan pages, orphan sources, stale articles, contradictions, missing backlinks, sparse articles. Details in [[concepts/hooks-and-scripts]].

## Scaling

At ~2,000+ articles, add hybrid RAG as a retrieval layer before the LLM.
