# cli-me Meta-Skill Knowledge Base

This wiki captures what the meta-skill has learned about building skills.
It self-improves as more skills are built.

## Pages

- [Learning Log](log.md) — chronological record of builds and lessons learned (21 entries)
- [Adversarial Review Prompts](../adversarial-reviewers.md) — 5 reviewer prompts + result handling protocol
- [Skill Template](../skill-template.md) — SKILL.md generation template
- [Wiki Template](../wiki-template.md) — wiki initialization template
- [Technique Page Template](../technique-page-template.md) — three-layer page structure
- [Typer CLI Template](../typer-cli-template.md) — modular CLI package structure
- [Write-Back Instructions](../write-back-instructions.md) — self-evolving section for generated skills

## Patterns Discovered

### Research Phase
- **Parallel agent research** scales linearly. 7 agents produced 35 technique pages
  in ~5 minutes. Each agent gets one category. No coordination needed.
- **Research agents cite URLs without verifying them.** Run `qa/check_urls.py`
  immediately after wiki creation, before adversarial review.
- **Source code analysis** (cloning the repo) finds the real API surface.
  Web research alone produces cargo-culted "best practices."

### Implementation Phase
- **Thin wrapper + logic layer** is the right architecture. CLI parses args and
  delegates to `commands/` module. Logic is independently testable.
- **One file per command group** keeps files focused. A single 1000+ line CLI file
  is unmaintainable and blocks parallel agent work.
- **`-y` (or equivalent)** must be added to every tool wrapper that has interactive
  prompts. Agent contexts don't have stdin.
- **Audio bitrate, pixel format, and codec profile** are the flags most likely to
  diverge between wiki documentation and code implementation. Always cross-reference.

### QA Phase
- **QA-first, not QA-last.** Write the playbook and Tier 1 tests before implementing
  commands. Test each command group as it's built. Never batch-implement-then-test.
- **Deep assertions from day one.** "File exists and is nonzero" catches nothing.
  Check exact dimensions, codecs, pixel formats, magic bytes, duration, file size.
- **Conditional assertions are traps.** If a prerequisite check fails, the test
  should fail — not silently skip the real assertion.
- **Deterministic tools beat LLM judgment** for anything mechanically checkable
  (URLs, file existence, format validation). Use scripts. Reserve LLMs for
  semantic issues.

### Adversarial Review Phase
- **Fresh context is non-negotiable.** Reviewer agents must not see the creator's
  conversation. Use a different model when possible.
- **Objective vs judgment split** prevents infinite loops and rubber-stamping.
  Objective failures auto-fix (3-strike limit). Judgment calls batch for human.
- **Code-wiki alignment (R3)** finds the most impactful issues. The pattern:
  agents write code that "works" but uses weaker settings than the wiki documents.
- **Zero-findings reviews are suspicious.** Re-dispatch with a harder prompt.
- **3 rounds** is what it took to get to a clean bill of health for ffmpeg.
  Expect 2-3 rounds for future skills.

## Pitfalls

### Things That Silently Break
- Missing `-pix_fmt yuv420p` — output plays in VLC but breaks in browsers/mobile
- Missing `-y` flag — ffmpeg hangs waiting for overwrite confirmation in agent context
- Missing `-profile:v high -level 4.0` for Twitter — uploads silently rejected
- `anullsrc` without `-shortest` — produces infinite/corrupted output
- Overlay filter input order `[1:v][0:v]` vs `[0:v][1:v]` — composites backwards
- Windows path colons in filter strings — ffmpeg parses `:` as option separator

### Things LLM Reviewers Miss
- Dead URLs (they spot-check; scripts check everything)
- Systemic patterns (128k vs 192k across 5+ commands — each looks fine individually)
- Interactive prompt hangs (reviewers test on their machine where the binary works)
- Conditional test assertions (the test "passes" so the reviewer marks it adequate)

### Things That Seem Fine But Aren't
- "File exists" assertions — any command that doesn't crash passes
- `"flag" in args` substring checks — too many false positives
- Wiki examples from web research — commands may be for older software versions
- Single-pass loudness normalization — produces audible pumping artifacts
