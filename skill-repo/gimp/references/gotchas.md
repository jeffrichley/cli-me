---
title: gotchas
tags: [gotchas]
sources:
  - https://www.gimp.org/man/gimp.html
  - https://www.gimp.org/tutorials/legacy/Basic_Batch
created: 2026-04-22
updated: 2026-04-22
---

# Gotchas

- GIMP may reuse an existing GUI instance unless `--new-instance` is set. This can
  make headless automation nondeterministic.
- Batch expressions are shell-quoted strings; Windows PowerShell/cmd quoting can break
  otherwise valid Scheme/Python expressions.
- If you omit `--quit` (or a terminal quit expression), non-interactive invocations can
  remain alive longer than expected.
- `--no-data` / `--no-fonts` improve startup time but can break scripts that rely on
  brushes/fonts/resources.
- Installed version parity is unverified in this environment because `gimp` is not on
  PATH; keep wrappers conservative and source/manpage-aligned.
