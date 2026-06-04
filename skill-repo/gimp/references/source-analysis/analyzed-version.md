---
title: analyzed-version
tags: [source-analysis, version]
sources:
  - tmp/source-analysis/gimp
created: 2026-04-22
updated: 2026-04-22
---

# Analyzed Version

- Repository: https://github.com/GNOME/gimp
- Commit: `67b65c598882e86b4d2acf0bc790e53fdb638bcc`
- Commit date: `2026-04-22T13:08:14+00:00`
- Describe: `67b65c5` (shallow clone, no tag available locally)
- Upstream branch identity from repo README: GIMP 3.2 stable branch
- Local installed binary check: `gimp --help` is unavailable on this machine (`gimp` not found on PATH)

## Release Alignment Note

Because GIMP is not installed in this environment, this skill cannot verify installed
flags against source-level flags yet. The wrapper therefore uses only options visible
in `app/main.c` and official man page docs, and avoids any unverified/development-only
flags in command examples.
