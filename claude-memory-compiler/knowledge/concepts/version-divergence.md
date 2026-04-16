---
title: Installed Version vs Source Repository Divergence
tags: [process, research]
sources: [daily/2026-04-15-seed.md]
created: 2026-04-16
updated: 2026-04-16
---

# Installed Version vs Source Repository Divergence

The installed (released) version of a tool may differ significantly from the cloned source repository. Features present in source may not exist in the PyPI/npm/apt release. Wrapping unreleased features causes multiple rounds of rework.

## The Demucs Case

The demucs source repo had `--other-method`, `--clip-mode none`, `--list-models`, and `demucs.api` — none of which existed in the PyPI 4.0.1 release. These were researched, documented, and partially implemented before the divergence was discovered.

## The Rule

Always run `binary --help` (or equivalent) on the **installed** version and compare against source analysis before wrapping any features. The installed binary is the source of truth for what the skill can use.

## Verification Step

Add to the research phase:

1. Analyze source repository for features and flags
2. Run installed binary's help/version output
3. Diff the two — flag any features present in source but absent from installed
4. Only wrap features confirmed present in the installed version

## Related Pattern

Device detection must also use the installed tool's Python, not the wrapper's. When the CLI runs in a uv venv but the tool is installed in system Python, `sys.executable` points to the wrong interpreter. Probe the tool's actual Python for environment-dependent behavior (CUDA/MPS/CPU detection).

See also: [[concepts/qa-before-implementation]], [[connections/interactive-prompts-in-agent-context]].
