---
title: api-surface
tags: [source-analysis, api]
sources:
  - https://www.gimp.org/man/gimp.html
  - https://developer.gimp.org/resource/script-fu/programmers-reference/
  - e:/workspaces/tools/cli-me/tmp/source-analysis/gimp/app/main.c
created: 2026-04-22
updated: 2026-04-22
---

# API Surface

GIMP automation is exposed through three practical surfaces relevant to this skill.

## 1) Command-line entrypoints

- `gimp` (GUI-capable binary)
- `gimp-console` (console-only binary, effectively no-interface mode)

Both support batch execution flags in the official man page and in `main_entries[]`
inside `app/main.c`.

## 2) Batch interpreter mechanism

`--batch` passes command strings to an interpreter. Interpreter selection:

- default: Script-Fu evaluator
- override: `--batch-interpreter <procedure>`

This means the wrapper can safely be a thin argv builder: it does not need to parse
Scheme/Python syntax itself, only pass user expressions to GIMP.

## 3) PDB-driven scripting layers

GIMP procedures are exposed via PDB to scripting runtimes:

- Script-Fu (Scheme dialect) for legacy and modern scripting
- Python-driven flows through batch interpreter procedure calls (`python-fu-eval`)

For cli-me scope, the skill wraps command dispatch and leaves script semantics to
the selected interpreter.
