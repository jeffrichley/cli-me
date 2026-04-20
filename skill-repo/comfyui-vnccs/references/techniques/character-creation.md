---
title: Character Creation (Stages 1 and 1.1)
tags: [vnccs, character, stage-1, stage-1.1, qwen, sdxl, pipeline-start]
sources:
  - upstream: https://github.com/AHEKOT/ComfyUI_VNCCS
  - readme: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md
  - workflow_step1: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step1_QWEN_CharSheetGenerator_v1.json
  - workflow_step1_1: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step1.1_QWEN_Clone_Existing_Character_v1.json
  - node_creator: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/character_creator.py
  - node_poser: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/pose_generator.py
  - poseset: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/presets/poses/vnccs_poseset.json
  - utils: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/utils.py
date: 2026-04-18
---

# Character Creation (Stages 1 + 1.1)

This is the very first thing you do with VNCCS. You can't build clothes, emotions, sprites, or a LoRA dataset until a character exists on disk, because every later stage reads from the character's on-disk state folder (`ComfyUI/output/VN_CharacterCreatorSuit/<CHARACTER_NAME>/`).

There are two entry routes:

- **Stage 1 — from-prompt.** Generate a brand-new character from a text description and a pose preset. Use this when you're designing a character from scratch.
- **Stage 1.1 — clone-existing.** Derive a VNCCS-registered character from an existing reference image (concept art, screenshot, full-body illustration). Use this when the character already "exists" visually but isn't yet in VNCCS's state.

Both stages end the same way: a 12-pose "character sheet" (2 rows x 6 columns) is written to `Sheets/Naked/neutral/sheet_neutral_<n>.png`, and a `<name>_config.json` is written next to it. Every later stage in the pipeline consumes those artifacts.

## When to use which stage

| Situation | Stage |
|---|---|
| You have a prompt like "red-haired elf girl, 17, freckles" | 1 |
| You have a single reference PNG of the character you want | 1.1 |
| You want to re-roll an existing character with a new seed | 1 (re-run with the same name) |
| You want to import a character from another VN / game / DeviantArt | 1.1 |

Stage 1.1 is forgiving about source images — it "imagines" missing parts — but the README explicitly recommends full-body images because partial references force the model to hallucinate limbs, which hurts consistency downstream.

## Parameters the wrapper exposes

The `VNCCS Character Creator` node (`nodes/character_creator.py`) takes these inputs, all of which the CLI maps to named flags:

| CLI flag | Node input | Notes |
|---|---|---|
| `--name` | `new_character_name` | Required for a new character; otherwise selects from `existing_character` dropdown. |
| `--existing` | `existing_character` | For re-rolls; omit if creating. |
| `--sex` | `sex` | `female` or `male`. |
| `--age` | `age` | Integer, 0-120. Drives `age_lora_strength` via the piecewise curve in `utils.age_strength`. |
| `--race` | `race` | Free-form string. |
| `--eyes` / `--hair` / `--face` / `--body` / `--skin-color` | same | Free-form. Each is wrapped in `(X:1.0)` prompt weighting. |
| `--additional-details` | `additional_details` | Catch-all appearance tokens. |
| `--aesthetics` | `aesthetics` | Defaults to `masterpiece,best quality,amazing quality`. |
| `--background-color` | `background_color` | Defaults to `green` (chroma key friendly). |
| `--nsfw` | `nsfw` | Boolean. Swaps the body-covering clause in the positive prompt. |
| `--negative-prompt` | `negative_prompt` | Defaults to `bad quality,worst quality`. |
| `--lora-prompt` | `lora_prompt` | Extra LoRA trigger tokens. |
| `--seed` | `seed` | 0 = randomize via `generate_seed`. |
| `--pose-preset` | (poser node) | Names resolve into `presets/poses/vnccs_poseset.json`. |
| `--steps` / `--checkpoint` | (KSampler / CheckpointLoader) | Patched into the workflow's sampler and model-loader nodes. |

The pose preset file ships a single `vnccs_poseset.json` containing a list of 12 poses on a 512x1536 canvas. The `VNCCS Pose Generator` node renders those into both a schematic and an OpenPose control image. The wrapper lists available presets by reading `vnccs_poseset.json` and any sibling JSONs a user has dropped into `presets/poses/`.

## Example CLI invocations

### Create a new character from a prompt (stage 1)

```bash
vnccs character create "Aria" \
  --sex female \
  --age 17 \
  --hair "red long wavy" \
  --eyes "green" \
  --face "freckles" \
  --body "petite" \
  --additional-details "elf ears, silver earring" \
  --pose-preset default \
  --seed 42
```

This submits `VN_Step1_QWEN_CharSheetGenerator_v1.json` to `/prompt` with the above values patched into the Character Creator node's widget_values and the Pose Generator node's pose selection. Output lands in `ComfyUI/output/VN_CharacterCreatorSuit/Aria/Sheets/Naked/neutral/sheet_neutral_1.png` (increments on re-run).

### Re-roll an existing character with a new seed

```bash
vnccs character create "Aria" --existing --seed 99
```

Same workflow; no `new_character_name` is passed, so the node loads the existing config, overrides the seed, and rewrites the sheet.

### Clone from a reference image (stage 1.1)

```bash
vnccs character clone "Ayase" \
  --reference ./refs/ayase_full_body.png \
  --sex female \
  --age 19 \
  --seed 0
```

This uses `VN_Step1.1_QWEN_Clone_Existing_Character_v1.json`. The reference image is uploaded via ComfyUI's `/upload/image` endpoint, and its filename is patched into the workflow's `LoadImage` node. The workflow then runs face detection, pose estimation, and a description pass before the same Character Creator output path.

### List what the wrapper knows about

```bash
vnccs character list
vnccs character show "Aria"
vnccs pose list
```

`character list` calls `utils.list_characters()` (it reads the subdirs of the base output dir). `pose list` enumerates keys from `presets/poses/vnccs_poseset.json`.

## What the pipeline produces

After a successful stage 1 run, the on-disk tree is:

```
ComfyUI/output/VN_CharacterCreatorSuit/
  Aria/
    Aria_config.json              # character_info + costumes (empty) + config_version
    Sheets/
      Naked/
        neutral/
          sheet_neutral_1.png     # 12-pose 2x6 grid, full-body, neutral face
    Faces/
      Naked/
        neutral/
          (populated later by stage 3)
    Sprites/
      Naked/
        neutral/
          (populated later by stage 4)
```

`Aria_config.json` is the single source of truth for every later stage. Its `character_info` block contains every appearance field you passed, plus the seed, so stage 2/3/4/5 can reconstruct a matching positive prompt without re-asking the user.

## Under the Hood

The stage-1 workflow is a long graph; the nodes that carry wrapper parameters are:

1. **VNCCS Character Creator** (`CharacterCreator`) — the entry point. Owns `new_character_name`, `sex`, `age`, `eyes`, `hair`, `face`, `body`, `skin_color`, `additional_details`, `nsfw`, `lora_prompt`, `negative_prompt`, `seed`, `background_color`, `aesthetics`. Outputs `positive_prompt`, `seed`, `negative_prompt`, `age_lora_strength`, `sheets_path`, `faces_path`, `face_details`. Also writes `<name>_config.json` as a side effect.
2. **VNCCS Pose Generator** (`VNCCSPoseGenerator`) — owns the pose preset JSON and emits both a schematic image (wired into a ControlNet preprocessor) and an OpenPose-format image (wired into the ControlNet conditioning). Canvas is fixed 512x1536 per pose, composed into a 3072x1024 sheet.
3. **CheckpointLoaderSimple + LoraLoader chain** — loads the illustrious/SDXL base + VNCCS LoRAs (`vn_character_sheet_v4.safetensors`, `DMD2/dmd2_sdxl_4step_lora_fp16.safetensors`, the age LoRA using `age_lora_strength`). The wrapper patches the checkpoint filename here.
4. **CLIPTextEncode (x2)** — positive and negative prompt text, wired from the Character Creator outputs.
5. **KSampler** — owns `seed`, `steps`, `cfg`, `sampler_name`, `scheduler`, `denoise`. The wrapper patches `seed` and `steps`.
6. **VAEDecode -> Sheet composition nodes** — first pass raw generation.
7. **VNCCS Sheet Manager** (`VNCCSSheetManager`) — splits the generated sheet into 12 parts, then recomposes them after a per-part refinement pass.
8. **Face Detailer + Upscaler** — per-pose face fix using `face_yolov8m.pt` / `face_yolov9c.pt`, then 2x/4x APISR upscale.
9. **VNCCS RMBG2** (`VNCCS_RMBG2`) — background removal using one of RMBG-2.0, INSPYRENET, BEN, BEN2. Controls background color and alpha.
10. **SaveImage** — final write to `Sheets/Naked/neutral/sheet_neutral_<n>.png`.

Stage 1.1 diverges at step 1: instead of the Character Creator emitting an initial prompt, a `LoadImage` node feeds the reference into a face/pose analysis chain (the "Clone" subgraph), which then synthesizes the `positive_prompt` that the rest of the pipeline uses. The remainder (steps 3-10) is identical to stage 1.

## Gotchas

- **Character name collisions.** `ensure_character_structure(name, ...)` in `utils.py` is idempotent — it won't raise if a character folder already exists. Running stage 1 with an existing name WILL overwrite `<name>_config.json` with the new `character_info` (costumes and emotions are preserved because the code reads-modifies-writes). The wrapper should surface a prompt before overwriting: call `vnccs character show <name>` first.
- **Missing required models.** The README lists a dozen models across checkpoints, LoRAs, ControlNet, face-detection, SAM, and upscalers. If any are missing, the `/prompt` submission returns HTTP 400 with a `node_errors` payload naming the missing file. The wrapper should run a pre-flight scan (per the sibling `comfyui` skill's model-check) and list missing files before submitting. See [../source-analysis/required-models.md](../source-analysis/required-models.md) if that sibling page exists.
- **Invalid pose preset.** If `--pose-preset` names a key not in `vnccs_poseset.json`, the Pose Generator falls back to `DEFAULT_SKELETON` and emits a warning to stdout. The wrapper should reject unknown preset names with exit 2 before submission; this is cheaper than debugging a silent fallback.
- **Age=0 is legal.** The `utils.age_strength` curve hits -5.0 at age 0; the LoRA-loader applies it directly. That's surprising for a "toddler" LoRA direction but it's in the config points. Warn (not block) if `--age < 5`.
- **Seed collisions when `--seed 0`.** `generate_seed(0)` returns a 64-bit random int. If the caller pipes multiple `create` commands in parallel without explicit seeds, the wrapper must capture each returned seed (read it back from `<name>_config.json`) before issuing the next command, so the sheets are reproducible.
- **SDXL vs QWEN.** The v2 stage-1 workflow is QWEN-based for the prompt expansion, but the actual diffusion is still SDXL/Illustrious. The older `V1SDXL/` workflows exist as a fallback (skill should expose a `--legacy-sdxl` flag for users on pure-SDXL model pools).
- **NSFW flag flips the positive prompt.** When `--nsfw` is true the prompt appends `(naked, nude, ...)` tokens; when false it appends `(wear white bra and panties)` or `(bare chest, wear white boxers)`. Downstream clothing generation relies on the character being generated near-naked so the costume layer can paint over — so do NOT pass `--nsfw false` AND then try to generate clothes over a fully-dressed base.
- **Stage 1.1 partial refs degrade quality.** The README explicitly says "try to use full body images" — it works with portraits but imagines missing legs/feet, which poisons downstream sprite rendering (stage 4 needs clean full-body sheets). Warn if the reference image's aspect ratio is wider than 1:1.5 (likely portrait-only).

## Sources

- [VNCCS README](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md) — pipeline overview and stage 1 / 1.1 descriptions.
- [VN_Step1_QWEN_CharSheetGenerator_v1.json](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step1_QWEN_CharSheetGenerator_v1.json) — stage 1 workflow graph.
- [VN_Step1.1_QWEN_Clone_Existing_Character_v1.json](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step1.1_QWEN_Clone_Existing_Character_v1.json) — stage 1.1 clone workflow.
- [nodes/character_creator.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/character_creator.py) — parameter-to-prompt translation, config persistence.
- [nodes/pose_generator.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/pose_generator.py) — pose preset loading.
- [presets/poses/vnccs_poseset.json](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/presets/poses/vnccs_poseset.json) — default pose set, 512x1536 canvas.
- [utils.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/utils.py) — directory layout, age curve, config I/O.
- Upstream repo: <https://github.com/AHEKOT/ComfyUI_VNCCS>
- Third-party node reference: <https://www.runcomfy.com/comfyui-nodes/ComfyUI_VNCCS>
- Civitai showcase: <https://civitai.com/models/2265016/vnccs-character-creation-suite>
