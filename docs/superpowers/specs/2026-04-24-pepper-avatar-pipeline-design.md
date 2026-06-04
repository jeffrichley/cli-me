# Pepper Avatar Pipeline Design

## Goal

Stand up a quality-first local pipeline for generating consistent Pepper avatars
using the newer Mickmumpitz Character Creator flow as the front end, FluxGym
for LoRA training, and a dedicated production render graph for final outputs.

The first release prioritizes identity consistency and signature visual traits
over throughput.

## Scope

In scope:

- Character Creator 3.8 as the primary hero and dataset generation flow
- one canonical hero-anchor selection process with explicit quality gates
- curated dataset creation for full-character LoRA objective
- FluxGym training workflow and checkpoint selection rubric
- production rendering with LoRA + PuLID + OpenPose + cleanup/upscale
- final 30-image deliverable aligned to Pepper's four-mode shot list

Out of scope:

- fallback strategy design unless first run fails
- end-to-end video generation branch
- cloud-first architecture (local-first remains default)
- implementing training inside a monolithic ComfyUI graph

## Primary Architecture

The pipeline is intentionally split into three stages:

1. Character Creator stage (ComfyUI):
   - locks hero identity and generates labeled dataset candidates
2. Training stage (FluxGym):
   - trains Pepper full-character LoRA using curated dataset
3. Production stage (ComfyUI):
   - generates and polishes final images using trained LoRA and control layers

This separation keeps debugging straightforward. Identity drift can be traced to
either dataset quality, training configuration, or render controls without
guesswork across one giant graph.

## Hardware Profile

Detected local GPU:

- `NVIDIA GeForce RTX 4060 Ti`
- ~16 GB VRAM (`16380 MiB`)

This supports a quality-first local run with moderate batch sizes and
checkpointed training.

## Identity Objective

The first LoRA cycle optimizes for full character package consistency:

- facial identity stability across pose and expression
- signature styling consistency (blazer family, earpiece logic, polish)
- mode flexibility without identity collapse

This objective is preferred over face-only because Pepper's recognizability
depends on both facial cues and signature styling.

## Dataset Contract

Target dataset size:

- 32-48 raw generated samples
- 28-40 curated training samples after filtering

Target composition:

- ~70% signature-on samples (blazer + earpiece visibility or clear inference)
- ~20% controlled variation samples (mode-specific expression/wardrobe shifts)
- ~10% edge samples (hard lighting, difficult angles, stronger expression)

Caption policy:

- include stable identity anchors on all examples
- keep style descriptors consistent but not over-constrained
- explicitly annotate mode/context when present

## Execution Blueprint

### Phase 0 - Environment Lock

- update ComfyUI
- import Character Creator 3.8 workflow and resolve required models
- configure deterministic output folders for hero, raw dataset, curated dataset,
  and renders
- run a smoke test for node and saver integrity

### Phase 1 - Hero Shot Lock

- generate hero candidates from fixed prompt scaffold with seed sweeps
- approve one canonical hero using hard checks:
  - front likeness
  - 3/4 likeness
  - eye and earpiece fidelity
- freeze seed and prompt metadata for reproducibility

### Phase 2 - Dataset Generation

- run Character Creator 3.8 from approved hero
- generate 32-48 samples with planned pose/expression/lighting spread
- run dataset creation/caption pass and export all raw artifacts

### Phase 3 - Curation and Caption Cleanup

- reject anatomy failures, severe drift, accessory hallucinations
- keep 28-40 best samples
- manually refine captions for high-leverage samples (hero-near + edge poses)

### Phase 4 - FluxGym Training

Baseline profile:

- rank: 32
- alpha: 16
- learning rate: 0.00015 (quality-first start)
- steps: 1400 baseline
- checkpoint every 400-500 steps

Checkpoint selection points:

- evaluate around 1000 and 1400 steps (optional 1800 if still improving)
- choose checkpoint by cross-pose identity retention, not single-image beauty

### Phase 5 - Production Generation

Render lock stack:

- Pepper LoRA: 0.8-0.95
- PuLID-Flux II: 0.55-0.7
- OpenPose ControlNet: moderate weight

Run in three passes:

- composition and pose pass
- identity tightening pass
- detail and upscale pass

### Phase 6 - Cleanup and Delivery

- apply Face Detailer on finalists
- upscale with conservative denoise (~0.3)
- export final shot pack and per-image generation metadata

## Quality Gates

Gate A (Hero):

- canonical hero approved against all hard checks

Gate B (Dataset):

- curated set maintains identity and signature coverage targets

Gate C (Training):

- selected checkpoint remains stable across pose/expression stress prompts

Gate D (Final):

- at least 24 of 30 finals pass identity + anatomy + mode-intent checks

## Success Criteria

The first run is successful when:

- pipeline executes end-to-end locally without structural blockers
- Pepper LoRA preserves full-character identity across the shot list
- final batch contains 30 usable images with four-mode coverage
- outputs are reproducible from stored seeds/prompts/checkpoint metadata

## Non-Goals

This design does not include:

- fallback path planning before first execution failure
- migration to cloud orchestration unless local constraints force it
- stylistic expansion beyond the defined Pepper identity and mode envelope
