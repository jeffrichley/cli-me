---
title: Node Surface
tags: [vnccs, nodes, api, workflow-patching]
source: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/
date: 2026-04-20
---

# Node Surface

This is the enumeration of every custom node class that VNCCS 2.1.0
registers with ComfyUI. The wrapper drives VNCCS by submitting ComfyUI
workflow graphs whose node inputs have been patched with the user's
arguments, so the **exact keys, types, and defaults** in each
`INPUT_TYPES` dict below are the contract the wrapper depends on.

**Class type vs display name**: in workflow JSON, nodes are identified by
their `type` field (the `class_type` in API format) which is the key in
`NODE_CLASS_MAPPINGS`. The "display name" is what ComfyUI shows in the
node palette; the wrapper should never rely on display name because it can
be re-localized. Both are listed below.

**Node count**: VNCCS registers **22 classes** across 14 Python modules.
All share `CATEGORY = "VNCCS"` (sometimes with a `VNCCS/pose`, `VNCCS/Util`,
or `VNCCS/encoding` sub-prefix).

## Character creation (stage 1)

### `CharacterCreator`

- **Display name**: `VNCCS Character Creator`
- **Module**: `nodes/character_creator.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `create_character`
- **Purpose**: Stage 1 entry point. Takes a character name + demographic
  fields, builds the positive/negative prompt, writes the character config
  JSON to disk, returns the SDXL prompt strings and the paths for sheet /
  faces outputs.

**INPUT_TYPES.required**:

| Key | Type | Default | Notes |
|---|---|---|---|
| `existing_character` | combo | first entry from `list_characters()` | Pre-populated from existing character directories. Selecting an existing name **re-uses** that character slot. |

**INPUT_TYPES.optional**:

| Key | Type | Default | Notes |
|---|---|---|---|
| `background_color` | STRING | `"green"` | |
| `aesthetics` | STRING multiline | `"masterpiece,best quality,amazing quality"` | Prepended to positive prompt. |
| `nsfw` | BOOLEAN | `False` | Drives the nude/clothing token selection (`nodes/character_creator.py:79-82`). |
| `sex` | combo | `"female"` (choices: `female`, `male`) | |
| `age` | INT 0-120 | `18` | Feeds `age_strength()` LoRA multiplier and `append_age()`. |
| `race` | STRING | `"human"` | |
| `eyes` | STRING | `"blue eyes"` | |
| `hair` | STRING | `"black long"` | |
| `face` | STRING | `"freckles"` | |
| `body` | STRING | `"medium breasts"` | |
| `skin_color` | STRING | `"white"` | |
| `additional_details` | STRING | `""` | |
| `seed` | INT 0-2⁶⁴-1 | `0` | `0` means "generate a fresh random seed". |
| `negative_prompt` | STRING multiline | `"bad quality,worst quality"` | |
| `lora_prompt` | STRING | `""` | Trigger tokens for any character LoRA. |
| `new_character_name` | STRING | `""` | Deprecated — `existing_character` already carries the name after the HTTP `/vnccs/create` endpoint pre-creates the slot. |

**RETURN_TYPES**: `(STRING, INT, STRING, FLOAT, STRING, STRING, STRING)`
**RETURN_NAMES**: `("positive_prompt", "seed", "negative_prompt", "age_lora_strength", "sheets_path", "faces_path", "face_details")`

The wrapper patches this node to set `existing_character` (the character
name) and the demographic fields.

---

### `CharacterPreview`

- **Display name**: `VNCCS Character Preview`
- **Module**: `nodes/character_preview.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `preview`
- **Purpose**: Simpler variant of `CharacterCreator` that returns only
  `(positive_prompt, seed, negative_prompt, age_lora_strength)` and does
  **not** write to the sheet/face directories. Supports batching by
  styles list — when `styles_list` is non-empty, returns lists
  (`OUTPUT_IS_LIST = (True, True, True, True)`) and appends
  `artist: {style}` to each prompt variant.

**INPUT_TYPES.required**: `character_name` (STRING, default `"NewCharacter"`)

**INPUT_TYPES.optional**: same demographic fields as `CharacterCreator`,
plus `styles_list` (LIST, default `[]`) for style batching.

**RETURN_TYPES**: `(STRING, INT, STRING, FLOAT)` with `OUTPUT_IS_LIST = (True, True, True, True)`

---

## Character selection (stage 2 / 3)

### `CharacterAssetSelector`

- **Display name**: `VNCCS Character Selector`
- **Module**: `nodes/character_selector.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `select`
- **Purpose**: Loads an existing character's info from the config JSON,
  applies costume overrides, emits positive / negative prompts, and loads
  the character's `Naked/neutral` sheet image as a torch tensor. Used in
  SDXL-style stage 2 and stage 3 workflows.

**INPUT_TYPES.required**:

| Key | Type | Default | Notes |
|---|---|---|---|
| `character` | combo | `list_characters()[0]` or `"None"` | |
| `costume` | combo | `"Naked"` | Collected from every character's saved costumes (`character_selector.py:35-42`). |

**INPUT_TYPES.optional**: `face`, `head`, `top`, `bottom`, `shoes`
(STRING, default `""`), `extra_negative_prompt` (STRING multiline),
`new_costume_name` (STRING).

**RETURN_TYPES**: `(STRING, STRING, STRING, STRING, INT, STRING, IMAGE)`
**RETURN_NAMES**: `("face_details", "face_path", "sheet_path", "positive_prompt", "seed", "negative_prompt", "character_sheet")`

---

### `CharacterAssetSelectorQWEN`

- **Display name**: `VNCCS Character Selector QWEN`
- **Module**: `nodes/character_selector.py` (second class)
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `select`
- **Purpose**: Same as `CharacterAssetSelector` but costume fields are
  multiline, and the node also emits a `costume_prompt` STRING that is a
  newline-joined summary of the populated costume parts — used by the
  QWEN image-edit pipeline.

Inputs identical to `CharacterAssetSelector` except `face`, `head`, `top`,
`bottom`, `shoes`, and `extra_negative_prompt` are all `multiline: True`.

**RETURN_TYPES**: adds a trailing `STRING` (`costume_prompt`) →
`(STRING, STRING, STRING, STRING, INT, STRING, IMAGE, STRING)`

---

## Emotion generation (stage 3)

### `EmotionGenerator`

- **Display name**: `VNCCS Emotion Generator`
- **Module**: `nodes/emotion_generator.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `generate_emotions`
- **Purpose**: Classic SDXL emotion generator. Scans all costume
  directories for the character, loads each costume's `neutral` sheet,
  and for every emotion in the comma-separated `emotions` input produces
  a (image, emotion text, face path, sheet path) tuple. The face path is
  duplicated **12 times** per emotion to match the 12-slot sheet layout.

**INPUT_TYPES.required**:

| Key | Type | Default | Notes |
|---|---|---|---|
| `character` | combo | first of `list_characters()` | |
| `emotions` | STRING multiline | `"angry,shy,smile,pout,sad,neutral"` | Comma-separated list. |
| `emotion_selector` | combo | `"happy"` | ~120 curated emotion labels in 6 groups (Emotions / Sexual / Smile / Smug / Surprised-Scared-Sad / Emotes). Hard-coded at `emotion_generator.py:33-69`. |

**RETURN_TYPES**: `(IMAGE, STRING, STRING, STRING, STRING, STRING, INT, MASK)`
**RETURN_NAMES**: `("image", "emotion", "face_output_path", "sheet_output_path", "positive_prompt", "negative_prompt", "seed", "mask")`
**OUTPUT_IS_LIST**: `(True, True, True, True, False, False, False, True)`

---

### `EmotionGeneratorV2`

- **Display name**: `VNCCS Emotion Studio`
- **Module**: `nodes/emotion_generator_v2.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `generate_emotions_v2`
- **Purpose**: Modern Emotion Studio. Takes the user's emotion + costume
  selections from the front-end as JSON-encoded strings, looks up each
  emotion in `emotions-config/emotions.json` (157 emotions across 9
  categories, keyed by `safe_name`), and produces the same output tuple
  as `EmotionGenerator` but with richer prompt construction ("QWEN Style"
  adds a natural-language prompt from `emotions.json[*].natural_prompt`).

**INPUT_TYPES.required**:

| Key | Type | Default | Notes |
|---|---|---|---|
| `prompt_style` | combo | `"SDXL Style"` (choices: `SDXL Style`, `QWEN Style`) | |
| `character` | combo | first of `list_characters()` or `"Character Name"` | |
| `costumes_data` | STRING | `"[]"` | JSON array of costume names. |
| `emotions_data` | STRING | `"[]"` | JSON array of emotion `safe_name`s. |

**RETURN_TYPES**: `(IMAGE, STRING, STRING, STRING, STRING, STRING, INT, MASK)`
Same return shape as v1. **OUTPUT_IS_LIST**: `(True, True, True, True, False, False, False, True)`.

Note: In `SDXL Style`, face paths are replicated 12× per emotion (for the
12-slot sheet). In `QWEN Style`, they are not (QWEN workflows do their own
mapping).

---

## Sprite and dataset output (stages 4 and 5)

### `SpriteGenerator`

- **Display name**: `VNCCS Sprite Generator`
- **Module**: `nodes/sprite_generator.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `generate_sprites`
- **Purpose**: Stage 4. Scans `Sheets/{costume}/{emotion}/` for the
  selected character, loads each sheet (using the highest-numbered
  `sheet_{emotion}_N.png` file), and produces image + mask tensor
  batches along with file path templates for `SaveImage`. Paths
  repeat 12× for the 12-slot sprite layout.

**INPUT_TYPES.required**: `character` (combo, `list_characters()[0]`)

**RETURN_TYPES**: `(IMAGE, STRING, MASK)`
**RETURN_NAMES**: `("images", "file_paths", "masks")`
**OUTPUT_IS_LIST**: `(True, True, True)`

---

### `DatasetGenerator`

- **Display name**: `VNCCS Dataset Generator`
- **Module**: `nodes/dataset_generator.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `generate_dataset`
- **Purpose**: Stage 5. Copies all `face_*.png` and `sprite_*.png` images
  from the character's `Faces/` and `Sprites/` directories into a flat
  `lora/` subdirectory, writing a `.txt` caption next to each image.
  Captions are assembled in `build_caption_text()` using the character
  config plus costume, emotion, and an optional `additional_caption`
  prefix.

**INPUT_TYPES.required**:

| Key | Type | Default |
|---|---|---|
| `character` | combo | `list_characters()[0]` |
| `game_name` | STRING | `"VN"` (prefix applied to caption — e.g. `VN_MyCharacter`) |

**INPUT_TYPES.optional**: `additional_caption` (STRING multiline, default `" "`)

**RETURN_TYPES**: `(STRING,)` → `("dataset_path",)`

---

## Sheet manipulation

### `VNCCSSheetManager`

- **Display name**: `VNCCS Sheet Manager`
- **Module**: `nodes/sheet_manager.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `process_sheet`
- **Purpose**: Splits a character sheet into 12 parts (2×6 grid) or
  composes 12 parts back into a square sheet. This is the core grid-op
  that makes the 12-pose sprite layout work. `INPUT_IS_LIST = True`.

**INPUT_TYPES.required**:

| Key | Type | Default | Notes |
|---|---|---|---|
| `mode` | combo | `"split"` (or `"compose"`) | |
| `images` | IMAGE | — | |
| `target_width` | INT 64-6144 step 64 | `1024` | Per-cell dim when splitting. |
| `target_height` | INT 64-6144 step 64 | `3072` | |

**INPUT_TYPES.optional**: `safe_margin` (BOOLEAN, default `False`) — when
composing, leaves a 4-px gap between cells and fills the background with
pure `#00FF00` for chroma keying.

**RETURN_TYPES**: `(IMAGE,)`, **OUTPUT_IS_LIST**: `(True,)`

---

### `VNCCSSheetExtractor`

- **Display name**: `VNCCS Sheet Extractor`
- **Module**: `nodes/sheet_manager.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `extract`
- **Purpose**: Returns one of the 12 sheet parts at a given index (0-5 is
  the top row, 6-11 is the bottom row). Internally wraps `VNCCSSheetManager.split_sheet()`.

**INPUT_TYPES.required**:

| Key | Type | Default |
|---|---|---|
| `image` | IMAGE | — |
| `part_index` | INT 0-11 | `0` |
| `target_width` | INT 64-6144 | `1024` |
| `target_height` | INT 64-6144 | `3072` |

**RETURN_TYPES**: `(IMAGE,)`

---

### `CharacterSheetCropper`

- **Display name**: `VNCCS Character Sheet Cropper`
- **Module**: `nodes/sheet_crop.py`
- **CATEGORY**: `VNCCS/Util`
- **FUNCTION**: `crop_character_sheet`
- **Purpose**: Uses `cv2.findContours(mask, RETR_EXTERNAL)` to locate
  individual characters on a sheet and crop each to its bounding box.
  Outputs a list of RGBA image tensors (alpha = original alpha or the mask).

**INPUT_TYPES.required**:

| Key | Type | Default |
|---|---|---|
| `image` | IMAGE | — |
| `mask` | MASK | — |
| `min_size` | INT 1-1024 | `64` |

**RETURN_TYPES**: `(IMAGE, MASK)`, **OUTPUT_IS_LIST**: `(True, True)`

---

### `VNCCSChromaKey`

- **Display name**: `VNCCS Chroma Key`
- **Module**: `nodes/sheet_manager.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `chroma_key`
- **Purpose**: RGB-distance-based green-screen removal with auto-detection
  of the key color from image borders (median of a 10%-wide border
  strip). Outputs a single RGBA IMAGE tensor with alpha = `1 - mask`.

**INPUT_TYPES.required**: `image` (IMAGE), `tolerance` (FLOAT 0-1 default
`0.2`), `despill_strength` (FLOAT 0-1 default `0.5`), `despill_kernel_size`
(INT 1-9 odd step 2 default `3`), `despill_color` (combo `interior_average` /
`black`).

**RETURN_TYPES**: `(IMAGE,)`

---

### `VNCCS_RMBG2`

- **Display name**: `VNCCS RMBG2`
- **Module**: `nodes/sheet_manager.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `process_image`
- **Purpose**: Background removal via one of four downloaded models:
  `RMBG-2.0`, `INSPYRENET`, `BEN`, `BEN2`. Models are downloaded on
  demand from Hugging Face to `models/RMBG/{model-name}/` using
  `huggingface_hub.hf_hub_download()`.

**INPUT_TYPES.required**: `image` (IMAGE), `model` (combo of the four names).

**INPUT_TYPES.optional**: `sensitivity` (FLOAT 0-1 default `1.0`),
`process_res` (INT 256-2048 step 8 default `1024`), `mask_blur` (INT 0-64
default `0`), `mask_offset` (INT -64 to 64 default `0`), `invert_output`
(BOOLEAN default `False`), `refine_foreground` (BOOLEAN default `False`),
`background` (combo `Alpha` / `Green` / `Blue`, default `Alpha`).

**RETURN_TYPES**: `(IMAGE, MASK, IMAGE)` — `(IMAGE, MASK, MASK_IMAGE)`.

---

### `VNCCS_QuadSplitter`

- **Display name**: `VNCCS Quad Splitter`
- **Module**: `nodes/sheet_manager.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `process`
- **Purpose**: Split a square image into 4 quadrants (`split` mode) or
  compose 4 quadrants into a 2×2 sheet (`compose` mode).

**INPUT_TYPES.required**: `mode` (combo `split` / `compose`), `image` (IMAGE).

**RETURN_TYPES**: `(IMAGE,)`, **OUTPUT_IS_LIST**: `(True,)`,
**INPUT_IS_LIST**: `True`.

---

### `VNCCS_Resize`

- **Display name**: `VNCCS Resize`
- **Module**: `nodes/sheet_manager.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `resize`

**INPUT_TYPES.required**: `image` (IMAGE), `width` (INT 1-8192 default
`512`), `height` (INT 1-8192 default `512`), `method` (combo: `nearest`,
`bilinear`, `bicubic`, `lanczos`; default `bilinear`).

**RETURN_TYPES**: `(IMAGE,)`

---

### `VNCCS_ColorFix`

- **Display name**: `VNCCS Color Fix`
- **Module**: `nodes/sheet_manager.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `color_fix`

**INPUT_TYPES.required**: `image` (IMAGE), `contrast` (FLOAT 0-2 step 0.01
default `1.0`), `saturation` (FLOAT 0-2 step 0.01 default `1.0`).

**RETURN_TYPES**: `(IMAGE,)`

---

### `VNCCS_MaskExtractor`

- **Display name**: `VNCCS Mask Extractor`
- **Module**: `nodes/sheet_manager.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `fill_alpha_with_color`
- **Purpose**: Flattens an RGBA image to RGB by compositing the alpha over
  a fixed `#00FF00` green background. (Input is `image` only — no color
  parameter; the green is hard-coded.)

**INPUT_TYPES.required**: `image` (IMAGE).

**RETURN_TYPES**: `(IMAGE,)` (renamed `IMAGE` in `RETURN_NAMES`).

---

## Pipe / utilities

### `VNCCS_Pipe`

- **Display name**: `VNCCS Pipe`
- **Module**: `nodes/vnccs_pipe.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `process_pipe`
- **Purpose**: Aggregates (MODEL, CLIP, VAE, positive/negative
  CONDITIONING, seed, steps, cfg, denoise, sampler_name, scheduler) into
  a single `VNCCS_PIPE` object that can thread through a workflow
  without wiring every individual noodle. Merges incoming pipe with
  per-port overrides (seed=0 means inherit; non-zero means override and
  propagate).

All inputs are optional. Relevant widget defaults observed in workflows:
`seed_int=0`, `sample_steps=0`, `cfg=0`, `denoise=0` or `684` (the number
is treated as-is; `684` appears to be a magic sentinel the user chose).

**RETURN_TYPES**: `(MODEL, CLIP, VAE, CONDITIONING, CONDITIONING, INT, INT, FLOAT, FLOAT, VNCCS_PIPE, SAMPLER_ENUM, SCHEDULER_ENUM)`

`SAMPLER_ENUM` and `SCHEDULER_ENUM` are populated at import time by
querying `comfy.samplers.KSampler.SAMPLERS` / `.SCHEDULERS`; fallback is
`["euler", "euler_a", "heun"]` / `["normal", "karras", "exponential"]`.

---

### `VNCCSSamplerSchedulerPicker`

- **Display name**: `VNCCS Sampler Scheduler Picker`
- **Module**: `nodes/sampler_scheduler_picker.py`
- **CATEGORY**: `VNCCS`
- **FUNCTION**: `pick`
- **Purpose**: Exposes ComfyUI's runtime sampler / scheduler enumerations
  as two dropdowns. Pure passthrough — returns the selected strings.

**INPUT_TYPES.required**: `sampler_name` (combo of `KSampler.SAMPLERS`),
`scheduler` (combo of `KSampler.SCHEDULERS`).

**RETURN_TYPES**: `(SAMPLER_ENUM, SCHEDULER_ENUM)` with same list content
as inputs.

---

### `VNCCS_QWEN_Encoder`

- **Display name**: `VNCCS QWEN Encoder`
- **Module**: `nodes/vnccs_qwen_encoder.py`
- **CATEGORY**: `VNCCS/encoding`
- **FUNCTION**: `encode`
- **Purpose**: Multi-reference image encoder for Qwen-Image-Edit. Takes a
  text prompt plus up to 3 reference images with per-image weights (0-2,
  quadratic mapping), encodes them through the CLIP + VAE pair, and
  returns `(positive, negative, latent)` conditioning for a KSampler.
  Honors the `reference_latents_method = "index_timestep_zero"` flag for
  QWEN 2511.

**INPUT_TYPES.required**: `clip` (CLIP), `prompt` (STRING multiline,
dynamicPrompts), `vae` (VAE).

**INPUT_TYPES.optional**: `latent_image_index` (INT 1-3 default `1`),
`image1`/`image2`/`image3` (IMAGE), `image1_name` / `image2_name` /
`image3_name` (STRING, defaults `"Picture 1"` / `"Picture 2"` /
`"Picture 3"`), `target_size` (combo: `1024`, `1344`, `1536`, `2048`,
`768`, `512`; default `1024`), `upscale_method` (combo: `lanczos`,
`bicubic`, `area`), `crop_method` (combo: `pad`, `center`, `disabled`),
`weight1`/`weight2`/`weight3` (FLOAT 0-2 step 0.01 default `1.0`),
`vl_size` (INT 256-1024 step 8 default `384`), `instruction` (STRING
multiline — long default describing the task), `qwen_2511` (BOOLEAN
default `True`).

**RETURN_TYPES**: `(CONDITIONING, CONDITIONING, LATENT)`

---

### `VNCCS_PoseGenerator`

- **Display name**: `VNCCS Pose Generator`
- **Module**: `nodes/pose_generator.py`
- **CATEGORY**: `VNCCS/pose`
- **FUNCTION**: `generate`
- **Purpose**: Renders 12 pose skeletons into a 6×2 grid on a black
  background, producing an OpenPose image tensor. Reads default 12-pose
  preset from `presets/poses/vnccs_poseset.json` (canvas 512×1536,
  BODY_25 joint names).

**INPUT_TYPES.required**:

| Key | Type | Default | Notes |
|---|---|---|---|
| `pose_data` | STRING multiline dynamicPrompts=False | (loaded from default preset) | JSON `{"canvas": {...}, "poses": [{"joints": {joint: [x, y], ...}}, ...]}` |
| `line_thickness` | INT 1-10 slider | `3` | |
| `safe_zone` | INT 0-100 slider | `100` | Scales poses toward canvas center by this % to avoid edge cropping. |

**RETURN_TYPES**: `(IMAGE,)` → `(openpose_grid,)`

Grid dimensions: `6 * 512 = 3072 wide` × `2 * 1536 = 3072 tall`.

---

## Passthrough helpers

### `VNCCS_Integer` / `VNCCS_Float` / `VNCCS_String` / `VNCCS_MultilineText` / `VNCCS_PromptConcat`

- **Module**: `nodes/common_nodes.py`
- **CATEGORY**: `VNCCS`
- **Purpose**: Thin wrappers so workflows can expose typed constants as
  dedicated nodes. Each has a single `value` input (or `a`/`b`/`c`/`d` +
  `separator` for `PromptConcat`) and a same-type output.

| Class | Display name | Input type | Default | Output |
|---|---|---|---|---|
| `VNCCS_Integer` | `VNCCS Integer` | INT [-2³¹, 2³¹-1] | `0` | INT |
| `VNCCS_Float` | `VNCCS Float` | FLOAT [-1e12, 1e12] step 0.01 | `0.0` | FLOAT |
| `VNCCS_String` | `VNCCS String` | STRING single-line | `""` | STRING |
| `VNCCS_MultilineText` | `VNCCS Multiline Text` | STRING multiline | `""` | STRING |
| `VNCCS_PromptConcat` | `VNCCS Prompt Concat` | 4 STRING + separator | `""`, `","` | STRING (omits empty parts) |

These passthroughs are heavily used in the provided workflows for the
wrapper-parameterizable knobs — e.g. the `SDXL Loader` subgraph wraps
`VNCCS_Integer` (steps) and `VNCCS_Float` (CFG) so the wrapper can patch a
single node to control numerics.

---

## Nodes referenced in workflows but not in VNCCS source

The `VN_Step3_QWEN_EmotionStudio_V1.json` workflow's `QWEN Detailer`
subgraph references two class names that are **not** defined in
`ComfyUI_VNCCS/nodes/*.py`:

- `VNCCS_QWEN_Detailer`
- `VNCCS_BBox_Extractor`

These are from a companion or newer unreleased module and will be missing
unless the user has an additional custom-node pack installed. The skill's
`vnccs check` command should flag this — attempting to run
`VN_Step3_QWEN_EmotionStudio_V1` without these nodes will produce a
`"Node type not found: VNCCS_QWEN_Detailer"` error from ComfyUI.

## Registration summary

All classes register via three parallel dicts in the nodes module that
aggregates them (`nodes/__init__.py`):

```python
NODE_CLASS_MAPPINGS = {
  "CharacterCreator": CharacterCreator,
  "CharacterPreview": CharacterPreview,
  "CharacterAssetSelector": CharacterAssetSelector,
  "CharacterAssetSelectorQWEN": CharacterAssetSelectorQWEN,
  "EmotionGenerator": EmotionGenerator,
  "EmotionGeneratorV2": EmotionGeneratorV2,
  "SpriteGenerator": SpriteGenerator,
  "DatasetGenerator": DatasetGenerator,
  "VNCCSSheetManager": VNCCSSheetManager,
  "VNCCSSheetExtractor": VNCCSSheetExtractor,
  "CharacterSheetCropper": CharacterSheetCropper,
  "VNCCSChromaKey": VNCCSChromaKey,
  "VNCCS_RMBG2": VNCCS_RMBG2,
  "VNCCS_QuadSplitter": VNCCS_QuadSplitter,
  "VNCCS_Resize": VNCCS_Resize,
  "VNCCS_ColorFix": VNCCS_ColorFix,
  "VNCCS_MaskExtractor": VNCCS_MaskExtractor,
  "VNCCS_Pipe": VNCCS_Pipe,
  "VNCCSSamplerSchedulerPicker": VNCCSSamplerSchedulerPicker,
  "VNCCS_QWEN_Encoder": VNCCS_QWEN_Encoder,
  "VNCCS_PoseGenerator": VNCCS_PoseGenerator,
  "VNCCS_Integer": VNCCS_Integer,
  "VNCCS_Float": VNCCS_Float,
  "VNCCS_String": VNCCS_String,
  "VNCCS_MultilineText": VNCCS_MultilineText,
  "VNCCS_PromptConcat": VNCCS_PromptConcat,
}
```

— 22 unique workflow-facing node types. The wrapper's `vnccs check`
command should iterate this list when confirming the custom-node pack is
loaded.

## Cross-references

- Workflow patching → [`workflow-stages.md`](workflow-stages.md)
- State directory layout → [`state-management.md`](state-management.md)
- Model files referenced by these nodes → [`required-models.md`](required-models.md)

## Sources

- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\__init__.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\character_creator.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\character_preview.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\character_selector.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\common_nodes.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\dataset_generator.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\emotion_generator.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\emotion_generator_v2.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\pose_generator.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\sampler_scheduler_picker.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\sheet_crop.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\sheet_manager.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\sprite_generator.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\vnccs_pipe.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\vnccs_qwen_encoder.py`
- https://github.com/AHEKOT/ComfyUI_VNCCS/tree/main/nodes
