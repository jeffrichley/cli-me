# comfyui-vnccs Skill Wiki

Agent-native wrapper for the ComfyUI_VNCCS visual novel character pipeline.
Composes on top of the sibling `comfyui` cli-me skill — this wrapper loads
bundled workflow JSONs, patches parameters, and hands off to ComfyUI for
actual generation.

**Pinned to VNCCS 2.1.0** (commit `7c3281f`). See
[bundled workflows README](../scripts/workflows/README.md) for the full
integrity table + Stage 3 upstream-bug note.

## Source Analysis

- [Analyzed Version](source-analysis/analyzed-version.md) — VNCCS 2.1.0, dependencies, minimum ComfyUI
- [Node Surface](source-analysis/node-surface.md) — 22 node classes documented (class_type, inputs, outputs, category)
- [Workflow Stages](source-analysis/workflow-stages.md) — 6 stages, parameterizable nodes, file naming
- [State Management](source-analysis/state-management.md) — where character sheets / costumes / emotions live on disk
- [Required Models](source-analysis/required-models.md) — 15 explicit files + 4 optional + 8 external packs

## Techniques

- [Character Creation](techniques/character-creation.md) — stages 1 + 1.1 (`character create / clone`)
- [Clothing Sets](techniques/clothing-sets.md) — stage 2 (`clothing add / list / remove / pick`)
- [Emotions](techniques/emotions.md) — stage 3 (`emotion add --legacy | --qwen`, plus `list / show / preview`)
- [Sprites and Datasets](techniques/sprites-and-datasets.md) — stages 4 + 5 (`sprite render`, `dataset export`)
- [Workflow and State Model](techniques/workflow-and-state-model.md) — pipeline dependency graph, parameter-patching mechanics, persistence conventions

## Operational

- [Log](log.md) — append-only build log
- [Gotchas](gotchas.md) — Stage 3 upstream bug, hardcoded output paths, and other footguns
- [Future Scope](future-scope.md) — v0.2 deferred features
- [Bundled Workflows](../scripts/workflows/README.md) — version + SHA-256 integrity table
