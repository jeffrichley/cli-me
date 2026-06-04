---
title: changelog
tags: [source-analysis, changelog]
sources:
  - e:/workspaces/tools/cli-me/tmp/source-analysis/gimp/NEWS
created: 2026-04-22
updated: 2026-04-22
---

# Changelog Notes Relevant to Automation

## 3.2.4 highlights

- Improved behavior for command-line-opened images in no-GUI/script contexts.
- Better temporary folder handling to avoid clashes.
- Script-Fu cleanup of deprecated functions in scripts.
- Improved PDF export plugin behavior.

## Wrapper implication

Automation wrappers should continue preferring no-interface + explicit batch execution
and avoid relying on deprecated Script-Fu patterns. Keep examples compatible with GIMP
3.x Script-Fu and explicit quit semantics.
