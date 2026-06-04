---
title: python-fu-batch-eval
tags: [technique, python-fu, batch]
sources:
  - https://www.gimp.org/man/gimp.html
  - https://www.gimp.org/tutorials/legacy/Basic_Batch
  - https://developer.gimp.org/resource/script-fu/programmers-reference/
created: 2026-04-22
updated: 2026-04-22
---

# Python-Fu Batch Eval

## When to Use

Use this when your automation logic is written as Python/PDB expressions rather than
Scheme Script-Fu expressions, and your local GIMP install actually exposes a Python
batch interpreter procedure.

## Technique

Select a Python-compatible batch interpreter and provide expression strings via
`--batch`. Start with a minimal quit expression to validate interpreter availability
before running larger commands.

## CLI Commands

```bash
gimp --no-interface --console-messages \
  --batch-interpreter python-fu-eval \
  --batch "pdb.gimp_quit(0)"
```

```bash
gimp --no-interface --console-messages \
  --batch-interpreter python-fu-eval \
  --batch "pdb.python_fu_example('input.png', 'output.png')" \
  --batch "pdb.gimp_quit(0)"
```

## Under the Hood

The CLI entrypoint remains the same; only the interpreter procedure changes via
`--batch-interpreter`. The wrapper can keep one argv model while allowing interpreter
selection.

## Learned from Usage

- Python interpreter availability and exact procedure names can vary by build/version.
  Validate locally with a trivial command first.
- Keep expressions short and shell-safe.
- On Windows, quoting/escaping often causes failures first; test with a trivial
  `pdb.gimp_quit(0)` command before larger expressions.
