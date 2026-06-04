---
title: key-functions
tags: [source-analysis, key-functions]
sources:
  - e:/workspaces/tools/cli-me/tmp/source-analysis/gimp/app/main.c
created: 2026-04-22
updated: 2026-04-22
---

# Key Functions

These source-level anchors are the most relevant for a CLI wrapper.

## `main_entries[]` (option table)

Defines automation-critical options:
- `--batch` / `--batch-interpreter`
- `--no-interface`
- `--new-instance`
- `--console-messages`
- `--quit`

Why it matters: this is the authoritative source for valid flag names and semantics.

## `main(...)`

Parses options, handles no-interface behavior, applies unique-instance routing, and
finally calls `app_run(...)` with parsed runtime state.

Why it matters: clarifies how batch/no-interface/new-instance interplay in real runs.

## `gimp_unique_open(...)` / `gimp_unique_batch_run(...)` path

When not forced into new-instance mode, work can be delegated to already running GIMP.

Why it matters: wrappers should default to deterministic, standalone process behavior.

## `gimp_show_version_and_exit(...)`

Version output path used by `--version`.

Why it matters: wrapper version command should be a direct subprocess pass-through.
