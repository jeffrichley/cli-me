---
title: Workflow Stages
tags: [vnccs, workflows, pipeline, patching]
source: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/
date: 2026-04-20
---

# Workflow Stages

VNCCS 2.1.0 ships six workflow JSONs covering the full character creation
pipeline. All six are **ComfyUI GUI-format** workflows (top-level keys:
`id`, `revision`, `last_node_id`, `last_link_id`, `nodes`, `links`,
`groups`, `definitions`, `config`, `extra`) — **not** API-format. To
execute a workflow via the `/prompt` endpoint the wrapper must first
convert GUI → API format, or ship pre-converted API workflows alongside
the skill.

The four QWEN workflows (`Step1`, `Step1.1`, `Step2`, `Step3`) make heavy
use of the **subgraph** feature: reusable node clusters declared in the
top-level `definitions.subgraphs` array and referenced from `nodes[].type`
by their UUID. This lets each workflow keep its visible canvas small (the
main `nodes[]` arrays are 16-51 nodes) while the real model loading and
sampling work happens inside ~5-10 subgraphs per workflow. **The wrapper
must descend into `definitions.subgraphs[].nodes[]` to patch model names,
LoRA paths, and KSampler parameters** — the top-level nodes only
parameterize the user-facing knobs.

## Subgraph cheat-sheet

These subgraph names recur across workflows:

| Subgraph name | Role | Contains |
|---|---|---|
| `QWEN Loader` | Loads the Qwen-Image-Edit model stack | `UnetLoaderGGUF`, `LoraLoaderModelOnly` (lightning LoRA), `CLIPLoader` (qwen_2.5_vl), `VAELoader`, `CFGNorm`, `ModelSamplingAuraFlow` |
| `SDXL Loader` | Loads the Illustrious SDXL checkpoint | `CheckpointLoaderSimple`, `VNCCSSamplerSchedulerPicker`, `VNCCS_Integer` (steps), `VNCCS_Float` (CFG) |
| `SDXL Core` | Per-SDXL-pass conditioning | `LoraLoader` (mimimeter), two `CLIPTextEncode`, two `PrimitiveString` |
| `Pose Generation` | Generate character in 12 poses | `VNCCS_QWEN_Encoder`, `LoraLoaderModelOnly` (poser_helper), `KSampler`, `VAEDecodeTiled`, `VNCCSSheetManager` (split), `VNCCS_RMBG2`, `PreviewImage`, `easy cleanGpuUsed` |
| `Character Generation` | SDXL sampling pass | `KSampler`, `ControlNetLoader` (openpose + AnytestV4), `ControlNetApplyAdvanced`, `FaceDetailer`, `UltralyticsDetectorProvider` (face_yolov8m), `UpscaleModelLoader` (APISR), `UltimateSDUpscale`, `VNCCS_RMBG2`, `VAEDecode`, `EmptyLatentImage` |
| `Face Detailer` | Re-detail face crops | `FaceDetailer`, `UltralyticsDetectorProvider` (bbox/face_yolov8m), `VNCCSChromaKey`, `easy cleanGpuUsed`, `VNCCS_String` |
| `Upscaler` | SeedVR2 + RMBG2 finishing pass | `SeedVR2LoadDiTModel`, `SeedVR2LoadVAEModel`, `SeedVR2VideoUpscaler`, `VNCCS_RMBG2`, `VNCCSSheetManager` (compose) |
| `Clothes Generator` | QWEN outfit generation | `VNCCS_QWEN_Encoder`, `LoraLoaderModelOnly` (ClothesHelperUltimateV1), `KSampler`, `AIO_Preprocessor` (DepthAnythingV2), `VNCCSSheetExtractor` |
| `Clothes replicator` | Propagate outfit across sheet | `VNCCS_QWEN_Encoder`, `LoraLoaderModelOnly` (TransferClothes), `KSampler`, `VNCCSSheetManager` (split) |
| `QWEN Detailer` | Stage-3 face detailer (qwen) | `VNCCS_QWEN_Detailer`, `VNCCS_BBox_Extractor`, `UltralyticsDetectorProvider` |
| `Remove Clothes` | (Step 1.1 only) nudify clone source | `KSampler`, `VNCCS_QWEN_Encoder`, `LoraLoaderModelOnly` (ClothesHelperUltimateV1) |
| `Settings` | Scalar constants for sampler/steps/CFG/denoise | `VNCCSSamplerSchedulerPicker`, `VNCCS_Integer`, `VNCCS_Float` |

---

## Stage 1 — `VN_Step1_QWEN_CharSheetGenerator_v1.json`

**Size**: 181 KB, 32 top-level nodes, 7 subgraph definitions.

**Purpose**: Create a brand-new character from scratch. The user supplies
a character name plus demographic fields (sex, age, race, hair, eyes,
body, skin color, etc.); the workflow generates a 12-pose character sheet
using Qwen-Image-Edit for pose generation and the Illustrious SDXL model
for the actual render passes (first pass, stabilizer, third pass, face
detailer, upscaler).

**Input requirements**:

- No prior stage output (this is the entry stage).
- Character template PNG (`character_template/CharacterSheetTemplate.png`,
  not referenced as a workflow input — it is the implicit base for
  pose grid compositing).

**Key parameterizable top-level nodes** (IDs refer to the node `id` in
`nodes[]`; patch these to drive the stage from the wrapper):

| Node ID | Type | Parameterizes |
|---|---|---|
| `499` | `CharacterCreator` | Character demographics — widgets `['Test', 'green', 'masterpiece', True, 'female', 18, 'human', 'blue eyes', 'black short', '', '', '', '', <seed>, 'bad quality,...', ...]` in the order declared by `CharacterCreator.INPUT_TYPES` — see [`node-surface.md`](node-surface.md). The first widget is the character name. |
| `585` | `VNCCS_PoseGenerator` | `pose_data` (JSON for 12 poses), `line_thickness`, `safe_zone`. |
| `382` | `Lora Loader Stack (rgthree)` | SDXL style LoRAs (4 slots). |
| `415` | `VNCCS_Pipe` | Seed override (first widget). `widgets_values[0]` is the seed. |
| `87` | `SaveImage` | Faces output filename prefix `'VN_Character/faces/face'`. |
| `15` | `SaveImage` | Sheet output filename prefix `'VN_Character/Body_Refined'`. |

**Key parameterizable subgraph nodes**:

- `SDXL Loader` subgraph → `CheckpointLoaderSimple` (id 4) →
  `ckpt_name = 'Illustrious\\ILFlatMix.safetensors'`. Change to swap the
  base SDXL checkpoint.
- `Character Generation` subgraph → `ControlNetLoader` (id 592) →
  `SDXL\\IllustriousXL_openpose.safetensors`; second `ControlNetLoader`
  (id 629) → `SDXL\\AnytestV4.safetensors`.
- `QWEN Loader` subgraph → `UnetLoaderGGUF` (id 617) →
  `qwen-image-edit-2511-Q5_0.gguf`; `LoraLoaderModelOnly` (id 619) →
  `qwen\\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`;
  `CLIPLoader` (id 624) → `qwen_2.5_vl_7b_fp8_scaled.safetensors`;
  `VAELoader` (id 625) → `qwen_image_vae.safetensors`.
- `Pose Generation` subgraph → `LoraLoaderModelOnly` (id 628) →
  `qwen\\VNCCS\\poser_helper_v2_000004200.safetensors` (strength 0.5).
- `Face Detailer` subgraph → `UltralyticsDetectorProvider` (id 537) →
  `bbox/face_yolov8m.pt`.
- `Character Generation` subgraph → `UpscaleModelLoader` (id 604) →
  `2x_APISR_RRDB_GAN_generator.pth`.
- `SDXL Core` subgraph → `LoraLoader` (id 632) → `IL\\mimimeter.safetensors`.
- `Upscaler` subgraph → `SeedVR2LoadDiTModel` (id 697) →
  `seedvr2_ema_3b_fp16.safetensors`; `SeedVR2LoadVAEModel` (id 696) →
  `ema_vae_fp16.safetensors`.

**Output**:

- Sheets — written by `SaveImage` id 15, prefix
  `VN_Character/Body_Refined` → lands in
  `ComfyUI/output/VN_Character/Body_Refined_NNNNN_.png`. **Note**: this
  prefix is ComfyUI's generic output dir, not the VNCCS state tree. The
  VNCCS-tree writes happen via `CharacterCreator` which calls
  `save_config()` and `ensure_character_structure()` from
  `utils.py` to create `ComfyUI/output/VN_CharacterCreatorSuit/{name}/`.
- Faces — `SaveImage` id 87, prefix `VN_Character/faces/face` →
  `ComfyUI/output/VN_Character/faces/face_NNNNN_.png`.

These are the publisher's defaults. The wrapper will likely want to
rewrite both prefixes to point to
`VN_CharacterCreatorSuit/{character}/Sheets/Naked/neutral/sheet_neutral`
so outputs land in the canonical VNCCS tree. See
[`state-management.md`](state-management.md).

**Required models** (see [`required-models.md`](required-models.md) for
download URLs and sizes):

- `qwen-image-edit-2511-Q5_0.gguf`
- `qwen\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`
- `qwen_2.5_vl_7b_fp8_scaled.safetensors`
- `qwen_image_vae.safetensors`
- `Illustrious\ILFlatMix.safetensors`
- `IL\mimimeter.safetensors`
- `SDXL\AnytestV4.safetensors`
- `SDXL\IllustriousXL_openpose.safetensors`
- `qwen\VNCCS\poser_helper_v2_000004200.safetensors`
- `bbox/face_yolov8m.pt`
- `2x_APISR_RRDB_GAN_generator.pth`
- `seedvr2_ema_3b_fp16.safetensors`
- `ema_vae_fp16.safetensors`

---

## Stage 1.1 — `VN_Step1.1_QWEN_Clone_Existing_Character_v1.json`

**Size**: 233 KB, 51 top-level nodes, 10 subgraph definitions.

**Purpose**: Clone an existing character image into the VNCCS sheet
layout. The user loads a reference image (`LoadImage` node id 638), the
workflow nudifies it (`Remove Clothes` subgraph) to establish a baseline,
re-poses it into 12 poses via QWEN, then writes a standard VNCCS sheet
just like Stage 1.

**Input requirements**:

- A single input image (`LoadImage` id 638 — default filename
  `f2b740ab53a3d8efbe81ee87b4f817f5.jpg` points to a sample; the wrapper
  must replace with the user's uploaded image).

**Key parameterizable top-level nodes**:

| Node ID | Type | Parameterizes |
|---|---|---|
| `499` | `CharacterCreator` | Demographics (same as Stage 1) plus seed. |
| `638` | `LoadImage` | Path to user-supplied reference image. |
| `585` | `VNCCS_PoseGenerator` | Target 12 poses. |
| `644` | `Text Find and Replace` | Used to rename `Naked` → `Original` when saving the cloned base (so that "Original" becomes a costume slot, not overwriting the true naked base). |
| `15` | `SaveImage` (title "Refined faces character sheet") | Sheet output. |
| `87` | `SaveImage` (title "Faces") | Faces output. |
| `645` | `SaveImage` | Another refined sheet output. |

**Additional subgraphs beyond Stage 1**:

- `Remove Clothes` (`9c6b0a26`) → uses
  `qwen\VNCCS\ClothesHelperUltimateV1_000005100.safetensors` (strength
  1.65) as the "nudify" LoRA. This runs before the main pose generation.

**Required models**: same as Stage 1, **plus** `ClothesHelperUltimateV1`.
Stage 1.1 does **not** use `SDXL\AnytestV4.safetensors`,
`SDXL\IllustriousXL_openpose.safetensors`, or
`2x_APISR_RRDB_GAN_generator.pth` — the Character Generation SDXL
subgraph is absent and replaced by pure QWEN pose generation.

---

## Stage 2 — `VN_Step2_QWEN_ClothesGenerator_v1.json`

**Size**: 112 KB, 18 top-level nodes, 5 subgraph definitions (`Settings`,
`Clothes Generator`, `Clothes replicator`, `QWEN Loader` variant, `Upscaler`
variants ×2).

**Purpose**: Add a new costume to an existing character. Uses
`Clothes Generator` subgraph to render the clothing on a single pose
(pose index 11 selected via `VNCCSSheetExtractor`), then
`Clothes replicator` propagates that outfit to all 12 poses of the
character's sheet.

**Input requirements**:

- Existing character (selected via `CharacterAssetSelectorQWEN`).
- Costume description as text (free-form wear descriptors).
- A new costume name.

**Key parameterizable top-level nodes**:

| Node ID | Type | Parameterizes |
|---|---|---|
| `579` | `CharacterAssetSelectorQWEN` | `widgets_values[0]` is character name (`'VNCCS_QWEN'` in sample), `[1]` costume name (`'armor'`), `[4]` is the top-wear text (`'Red mecha-bio-armor'` in sample). Also `new_costume_name` at `[9]`. |
| `577`, `576`, `575` | `VNCCS_Pipe` | Seed overrides (widget 0). |
| `610` | `VNCCSSheetExtractor` | `part_index=11` — selects the bottom-right pose (arm-up standing frontal) as the reference for clothing generation. |
| `610`.`part_index` | INT | Which of the 12 poses to use as the clothes-gen reference. |
| `15` | `SaveImage` | Output prefix `VN_Character/Body_Refined`. |

**Key parameterizable subgraph nodes**:

- `Clothes Generator` subgraph → `LoraLoaderModelOnly` (id 633) →
  `qwen\VNCCS\ClothesHelperUltimateV1_000005100.safetensors` (strength
  1.65); `AIO_Preprocessor` (id 646) → `DepthAnythingV2Preprocessor` at
  resolution 512.
- `Clothes replicator` subgraph → `LoraLoaderModelOnly` (id 666) →
  `qwen\VNCCS\TransferClothes_000006700.safetensors` (strength 1.15).
- `QWEN Loader` subgraph — same models as Stage 1.
- `Upscaler` subgraph(s) — `seedvr2_ema_3b_fp16.safetensors` +
  `ema_vae_fp16.safetensors`.

**Output**:

- Via `SaveImage` id 15, prefix `VN_Character/Body_Refined`.
- The actual VNCCS-tree writes happen through
  `CharacterAssetSelectorQWEN.select()` which calls
  `save_costume_info(character, costume, costume_data)` — this writes the
  new costume entry into
  `ComfyUI/output/VN_CharacterCreatorSuit/{character}/{character}_config.json`
  under `config["costumes"][costume_name] = { face, head, top, bottom, shoes }`.

**Required models**: `qwen-image-edit-2511-Q5_0.gguf`, lightning LoRA,
qwen CLIP + VAE, `ClothesHelperUltimateV1`, `TransferClothes`,
`seedvr2_ema_3b_fp16`, `ema_vae_fp16`. Stage 2 does **not** require any
SDXL checkpoint, ControlNet, or face detailer — it is pure QWEN.

---

## Stage 3 — `VN_Step3_QWEN_EmotionStudio_V1.json`

**Size**: 43 KB, 16 top-level nodes, 3 subgraph definitions (`QWEN
Loader`, `QWEN Detailer`, `Settings`).

**Purpose**: Generate emotion variants for selected costume sheets. For
each (costume × emotion) pair the user selects in the Emotion Studio
panel, the workflow produces a full 12-pose sheet with that emotion
applied to every face.

**Input requirements**:

- Existing character with at least one costume sheet (`Naked/neutral` or
  any custom costume).
- List of selected costume names (JSON string).
- List of selected emotion `safe_name`s (JSON string) — these map into
  `emotions-config/emotions.json`.

**Key parameterizable top-level nodes**:

| Node ID | Type | Parameterizes |
|---|---|---|
| `69` | `EmotionGeneratorV2` | `widgets_values`: `[prompt_style, character, costumes_data_json, emotions_data_json, <reserved>]`. Sample: `['QWEN Style', 'Alina', '["Naked","Casual"]', '["radiant-smile"]', '']`. |
| `55`, `40`, `39` | `VNCCS_Pipe` | Seed / sampling defaults. |
| `9` | `SaveImage` | Output prefix (sample: `VN_Lora/Anya/dataset/faces/face_happy`). |
| `19` | `SaveImageWithAlpha` | Sprite prefix (sample: `VN_Character/sprites/sprite`). |

**Key parameterizable subgraph nodes**:

- `QWEN Loader` (`53029c38`) — the standard QWEN stack (GGUF, lightning
  LoRA, qwen CLIP, qwen VAE).
- `QWEN Detailer` (`8881761a`) — `LoraLoaderModelOnly` (id 72) →
  `qwen\VNCCS\EmotionCoreV1_000003000.safetensors` (strength 1);
  two `UltralyticsDetectorProvider` nodes (ids 71, 77) →
  `bbox/face_yolov8m.pt`.
- **Warning**: This subgraph references two node types
  (`VNCCS_QWEN_Detailer`, `VNCCS_BBox_Extractor`) that **do not exist in
  VNCCS 2.1.0 source**. See [`node-surface.md`](node-surface.md) "Nodes
  referenced in workflows but not in VNCCS source". The wrapper's
  `vnccs check` command should warn when these node types are missing
  from the ComfyUI registry.

**Output**:

- The workflow calls `EmotionGeneratorV2.generate_emotions_v2()` which
  builds `face_output_paths` and `sheet_output_paths` as:
  `{character_dir}/Faces/{costume}/{emotion}/face_{emotion}_` and
  `{character_dir}/Sheets/{costume}/{emotion}/sheet_{emotion}_`.
  These are the prefixes ComfyUI's `SaveImage` appends sequence numbers
  to — the VNCCS-tree writes are automatic.

**Required models**: QWEN Loader stack + `EmotionCoreV1` LoRA +
`bbox/face_yolov8m.pt`. No SDXL checkpoint, no upscaler.

---

## Stage 4 — `VN_Step4_CharSpriteCreatorV5.json`

**Size**: 2.4 KB, **3 top-level nodes**, no subgraphs.

**Purpose**: Extract individual sprites from the generated emotion
sheets. This is a thin workflow that just wires `SpriteGenerator` →
`CharacterSheetCropper` → `SaveImage`.

**Nodes**:

| Node ID | Type | Widgets |
|---|---|---|
| `1` | `SpriteGenerator` | `['VNCCS_MASCOT']` — first widget is the character name. |
| `4` | `CharacterSheetCropper` | `[128, 3072]` → `min_size=128`, the second value appears to be `target_height` (the cropper has no `target_height` in its INPUT_TYPES — this is likely orphan; actual widgets in use are just `min_size`). |
| `5` | `SaveImage` | `['ComfyUI']` — generic prefix. |

**Key parameterizable node**: `SpriteGenerator` (id 1) → `character`.

**Input requirements**: A character with generated emotion sheets in
`Sheets/{costume}/{emotion}/` (produced by Stage 3).

**Output**: `SpriteGenerator` returns `file_paths` that are shaped like
`{character_dir}/Sprites/{costume}/{emotion}/sprite_{emotion}_`;
`SaveImage` appends sequence numbers. But because this workflow sets
`SaveImage.filename_prefix = 'ComfyUI'`, the actual filesystem write
lands under `ComfyUI/output/ComfyUI_NNNNN_.png` — **the wrapper must
patch `SaveImage` node 5 to use the file_paths output from
`SpriteGenerator`** if it wants the sprites to land in the VNCCS tree.

**Required models**: None. Pure image-op workflow.

---

## Stage 5 — `VN_Step5_LoraDataSetGeneratorV5.json`

**Size**: 1.1 KB, **2 top-level nodes**, no subgraphs.

**Purpose**: Export a flat LoRA training dataset (image + caption pairs)
for the selected character. Copies files from `Faces/` and `Sprites/`
into a `lora/` subdirectory and writes per-file `.txt` captions.

**Nodes**:

| Node ID | Type | Widgets |
|---|---|---|
| `7` | `DatasetGenerator` | `['NewCharacter1', 'VN', ' ']` → `character`, `game_name`, `additional_caption`. |
| `8` | `Save Text File` | `['', './ComfyUI/output/[time(%Y-%m-%d)]', 'ComfyUI', '_', 4, '.txt', 'utf-8', '']` — uses an external custom node (Save Text File). |

**Key parameterizable node**: `DatasetGenerator` (id 7) — `character` and
`game_name`.

**Input requirements**: A character with generated face crops in
`Faces/{costume}/{emotion}/face_*.png` and sprites in
`Sprites/{costume}/{emotion}/sprite_*.png`.

**Output**: `{character_dir}/lora/` (note: lowercase `lora/` per
`DatasetGenerator.generate_dataset`, though other parts of the tree use
title-case `Faces/Sheets/Sprites`). Contains:
- `{costume}_{emotion}_face_{emotion}_NNNNN.png` (copied from Faces/)
- `{costume}_{emotion}_sprite_{emotion}_NNNNN.png` (copied from Sprites/)
- `.txt` next to each image with the assembled caption.

**Required models**: None.

---

## Summary table

| Stage | File | Top-level nodes | Subgraphs | Wrapper-patch node count | Writes to VNCCS tree? |
|---|---|---|---|---|---|
| 1 | `VN_Step1_QWEN_CharSheetGenerator_v1.json` | 32 | 7 | ~6 top + ~10 subgraph-internal | Yes (via `CharacterCreator`) |
| 1.1 | `VN_Step1.1_QWEN_Clone_Existing_Character_v1.json` | 51 | 10 | ~8 top + ~12 subgraph-internal | Yes (via `CharacterCreator` + `Remove Clothes`) |
| 2 | `VN_Step2_QWEN_ClothesGenerator_v1.json` | 18 | 5 | ~4 top + ~8 subgraph-internal | Yes (via `CharacterAssetSelectorQWEN.save_costume_info`) |
| 3 | `VN_Step3_QWEN_EmotionStudio_V1.json` | 16 | 3 | 1 top (`EmotionGeneratorV2`) + subgraph models | Yes (emit paths; SaveImage honors them) |
| 4 | `VN_Step4_CharSpriteCreatorV5.json` | 3 | 0 | 1 top (`SpriteGenerator`); SaveImage rewrite | Yes (if SaveImage patched) |
| 5 | `VN_Step5_LoraDataSetGeneratorV5.json` | 2 | 0 | 1 top (`DatasetGenerator`) | Yes (`lora/` subdirectory) |

## Legacy workflows

`workflows/V1SDXL/` and `workflows/old_workflows/` contain earlier v4 /
v4.1 / v5 SDXL-only workflows. The wrapper should **not** use these for
MVP — the 2.1.0 release's QWEN workflows are the supported path. Legacy
workflows are kept for users without QWEN models.

## Sources

- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\workflows\VN_Step1_QWEN_CharSheetGenerator_v1.json`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\workflows\VN_Step1.1_QWEN_Clone_Existing_Character_v1.json`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\workflows\VN_Step2_QWEN_ClothesGenerator_v1.json`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\workflows\VN_Step3_QWEN_EmotionStudio_V1.json`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\workflows\VN_Step4_CharSpriteCreatorV5.json`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\workflows\VN_Step5_LoraDataSetGeneratorV5.json`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\README.md`
- https://github.com/AHEKOT/ComfyUI_VNCCS/tree/main/workflows
