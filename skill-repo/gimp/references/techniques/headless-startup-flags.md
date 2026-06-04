---
title: headless-startup-flags
tags: [technique, headless, performance]
sources:
  - https://www.gimp.org/man/gimp.html
  - https://github.com/GNOME/gimp/blob/master/app/main.c
created: 2026-04-22
updated: 2026-04-22
---

# Headless Startup Flags

## When to Use

Use this for CI, agent execution, or any environment where GUI prompts must never
appear and startup cost should be minimized.

## Technique

Use non-interactive defaults and force a new process for deterministic behavior.

## CLI Commands

```bash
gimp --new-instance --no-interface --console-messages --no-splash --batch "(gimp-quit 0)"
```

```bash
gimp --new-instance --no-interface --console-messages --no-data --no-fonts \
  --batch "(gimp-quit 0)"
```

## Under the Hood

- `--new-instance` avoids reuse of running GIMP instances.
- `--no-interface` suppresses GUI.
- `--console-messages` sends warnings/errors to stderr/stdout instead of dialogs.
- `--no-data` and `--no-fonts` reduce startup loading for purely procedural runs.

## Learned from Usage

- Keep `--console-messages` on by default so batch failures are visible in logs.
- Add `--no-data` and `--no-fonts` only when scripts do not depend on those assets;
  otherwise scripts may fail due to missing resources.
