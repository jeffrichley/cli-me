---
title: script-fu-batch-basics
tags: [technique, script-fu, batch]
sources:
  - https://www.gimp.org/tutorials/legacy/Basic_Batch
  - https://www.gimp.org/man/gimp.html
created: 2026-04-22
updated: 2026-04-22
---

# Script-Fu Batch Basics

## When to Use

Use this when you need deterministic, repeatable image edits from the terminal without
opening the GUI.

## Technique

Pass one or more Script-Fu expressions via repeated `--batch` flags. Always end with
an explicit quit command so the process does not linger.

## CLI Commands

```bash
gimp --no-interface --console-messages --batch "(gimp-quit 0)"
```

```bash
gimp --no-interface --console-messages \
  --batch "(simple-unsharp-mask \"input.png\" 5.0 0.5 0)" \
  --batch "(gimp-quit 0)"
```

## Under the Hood

`--batch` strings are evaluated by the currently selected batch interpreter (Script-Fu
by default). GIMP parses flags in `app/main.c` and forwards command strings to the
interpreter runtime.

## Learned from Usage

- Prefer explicit `--quit` or `(gimp-quit 0)` in non-interactive runs.
- Keep quoting simple and test platform-specific escaping in Windows shells.
