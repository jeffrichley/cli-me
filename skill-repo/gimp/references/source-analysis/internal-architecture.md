---
title: internal-architecture
tags: [source-analysis, architecture]
sources:
  - e:/workspaces/tools/cli-me/tmp/source-analysis/gimp/app/main.c
  - https://developer.gimp.org/resource/script-fu/programmers-reference/
created: 2026-04-22
updated: 2026-04-22
---

# Internal Architecture

## Startup and option parsing

`app/main.c` owns process startup and command-line parsing via `GOptionEntry`.
Flags populate static globals (`no_interface`, `batch_commands`, `batch_interpreter`,
etc.) then flow into `app_run(...)`.

## Instance reuse behavior

When GUI mode is enabled and `--new-instance` is not set, GIMP may forward work to an
existing process (`gimp_unique_open(...)`). For deterministic automation, wrappers
should prefer `--new-instance`.

## Batch processing flow

Batch commands are collected as string arrays and evaluated through the selected
interpreter procedure. This is intentionally interpreter-agnostic at the CLI layer.

## Script-Fu architecture notes

Script-Fu is interpreter-based and backed by PDB bindings. Modern GIMP 3 adds
new-style plug-in registration and separate-process execution patterns for scripts in
`plug-ins` with the expected shebang model.
