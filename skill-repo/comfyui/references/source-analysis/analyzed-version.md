# Analyzed Version

This document records the exact ComfyUI source revision that the other files in `source-analysis/` describe. Every file:line reference in this directory points into this commit.

## Version strings

- `comfyui_version.__version__` = `"0.19.0"` (from `E:\workspaces\tools\comfy\ComfyUI\comfyui_version.py:3`)
- `git describe --tags --always` = `v0.19.0` (tagged release, clean)
- `git log -1` HEAD:

```
commit  acd718598eca0b944a1a7a82072a9dec40d3d4f7
message ComfyUI v0.19.0
date    2026-04-13 03:02:36 -0400
```

## Analysis metadata

- Date analyzed: 2026-04-18
- Source tree on disk: `E:\workspaces\tools\comfy\ComfyUI\`
- Installed release matches the tag exactly: the `__version__` constant in `comfyui_version.py` agrees with the `v0.19.0` git tag on HEAD, so the on-disk tree is the clean release (not a post-tag development snapshot).
- `comfyui_version.py` is auto-generated from `pyproject.toml` during the build, per its own header comment (`comfyui_version.py:1-2`).

## Scope of this analysis

All 5 documents in this directory were written against this exact revision. If the ComfyUI source tree is upgraded later, re-run the skill's source-analysis phase before trusting these files.
