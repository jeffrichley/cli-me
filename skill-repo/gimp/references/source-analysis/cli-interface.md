---
title: cli-interface
tags: [source-analysis, cli]
sources:
  - https://www.gimp.org/man/gimp.html
  - e:/workspaces/tools/cli-me/tmp/source-analysis/gimp/app/main.c
created: 2026-04-22
updated: 2026-04-22
---

# CLI Interface

This page records the automation-relevant options from GIMP's current source/manpage.

## Core non-interactive flags

- `-i`, `--no-interface`: run without GUI
- `-b`, `--batch <command>`: run a batch command, repeatable
- `--batch-interpreter <procedure>`: interpreter for batch commands
- `--quit`: quit after requested actions
- `-c`, `--console-messages`: route messages to console

## Startup/perf flags useful in wrappers

- `-n`, `--new-instance`: force a new process instead of reusing running instance
- `-d`, `--no-data`: skip brushes/gradients/patterns load
- `-f`, `--no-fonts`: skip fonts
- `-s`, `--no-splash`: disable splash
- `--verbose`: print verbose startup info

## Batch invocation patterns

- Single expression:
  - `gimp -i -b '(gimp-quit 0)'`
- Multiple expressions:
  - `gimp -i -b '(expr-1 ...)' -b '(expr-2 ...)' -b '(gimp-quit 0)'`
- STDIN expression stream:
  - `gimp -i -b -`

## Installed-version parity status

Installed binary is unavailable in this environment, so parity between source and
installed flags is not yet verified. The wrapper only uses options documented in both
`app/main.c` and the official man page.
