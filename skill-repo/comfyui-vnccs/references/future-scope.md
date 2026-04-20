# comfyui-vnccs — v0.2 Deferred Features

The v0.1 scope covers the 6-stage VNCCS pipeline end-to-end for a single
character workflow. The following are intentionally deferred.

## Per-costume sprite filtering

Currently `sprite render` renders every (costume × emotion) combo on
disk. Users wanting to render only a subset have to delete other
costume/emotion directories first. A `--costume` / `--emotion` filter
would require either:
- Forking VNCCS's `sprite_generator.py` to add the filter upstream
- Post-rendering filtering (delete files after, wasteful)
- Patching the workflow JSON to inject filter nodes

Defer until users actually request it — the render-everything behavior
matches the VN production workflow (one character → full sprite sheet).

## QWEN emotion workflow (when upstream fixes it)

`vnccs emotion add --qwen` exists as an escape hatch, but the default is
`--legacy`. When upstream ships the `VNCCS_QWEN_Detailer` and
`VNCCS_BBox_Extractor` classes, flip the default to `--qwen` and keep
`--legacy` as opt-in for users who want the SDXL pipeline.

## Batch character creation

Right now `character create` generates one character at a time. A
`character batch --from-yaml characters.yaml` would let agents create
multiple characters in one invocation. Requires careful concurrency
handling since each submit blocks on ComfyUI.

## Character portrait variants (multiple expressions per emotion)

VNCCS's emotion stage generates one sheet per (costume, emotion). Some
VN workflows want N variants per emotion (different head tilts, blush
levels). Would require workflow JSON patching to adjust the batch size
per submission.

## Integration with LoRA training

`dataset export` produces a kohya-ss-compatible dataset but doesn't
kick off training. A `vnccs lora train CHARACTER --out ./loras/aria`
command that calls the sibling `kohya-ss` skill (not yet built) would
close the full loop from "character concept" to "trained LoRA".

## VNCCS cleanup branch adoption

The upstream `cleanup` branch has a major rewrite in progress:
`vnccs_control_center.py`, `character_cloner.py`, `clothes_designer.py`,
`sprite_manager.py`, v2.3 workflows. When that branch merges to `main`
and gets a tagged release, update this skill to pin to the new version.

## ComfyUI-Manager integration

ComfyUI-Manager provides an in-app UI for installing/updating custom
nodes. Our `comfyui custom-nodes install` is the CLI equivalent. A
feature to sync VNCCS's required-packs list into ComfyUI-Manager's
config would make the "open ComfyUI → install these packs" path
one-click for humans.

## NOT planned

- **Custom sprite workflows** — VNCCS's 6 workflows are opinionated for
  VN production. Users wanting custom pipelines should go through
  ComfyUI directly or build their own skill.
- **Real-time character preview** — outside the scope of an agent CLI.

## When to promote v0.2 → v0.3

Triggers: upstream VNCCS releases 2.2.0+ with the missing nodes, Jeff's
pipeline surfaces a concrete need for one of the above, or a user asks.
Don't pre-build.
