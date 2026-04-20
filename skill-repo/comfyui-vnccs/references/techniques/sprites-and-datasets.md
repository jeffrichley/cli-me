---
title: Sprite Rendering and LoRA Dataset Export (Stages 4 + 5)
tags: [vnccs, sprites, rendering, lora, dataset, stage-4, stage-5, pipeline-end]
sources:
  - upstream: https://github.com/AHEKOT/ComfyUI_VNCCS
  - readme: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md
  - workflow_step4: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step4_CharSpriteCreatorV5.json
  - workflow_step5: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step5_LoraDataSetGeneratorV5.json
  - node_sprite: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/sprite_generator.py
  - node_dataset: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/dataset_generator.py
  - node_sheetcrop: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/sheet_crop.py
  - utils: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/utils.py
date: 2026-04-18
---

# Sprite Rendering and LoRA Dataset Export (Stages 4 + 5)

These are the terminal stages. Stage 4 converts the multi-pose sheets and face crops from stages 1-3 into VN-ready per-pose sprite PNGs with clean alpha. Stage 5 assembles all the images + auto-generated captions into a Kohya-ss-compatible LoRA training dataset.

## When to use

- **Stage 4** — once you're happy with the costume + emotion set for a character. This is the slow step: for every (costume x emotion) combination the character has on disk, stage 4 produces 12 sprites (one per pose). A character with 4 costumes and 10 emotions = 480 sprites.
- **Stage 5** — after stage 4 is complete AND you want to train a LoRA of this character. If you don't plan to train, skip stage 5.

Neither stage needs any user-authored prompt text. All parameters are inferred from the character's on-disk state.

## Stage 4 — Sprite Rendering

### Parameters

| CLI flag | Node input | Notes |
|---|---|---|
| `--character` | `SpriteGenerator.character` (COMBO) | Enumerated from `list_characters()`. |
| `--costume` | (filter applied by wrapper) | Optional; defaults to all. |
| `--emotion` | (filter applied by wrapper) | Optional; defaults to all. |
| `--output-format` | `SaveImage.filename_prefix` + extension | PNG default. WebP supported via a `SaveImageWebP` swap. |
| `--output-resolution` | `CharacterSheetCropper.target_height` | Default 3072 (per-pose canvas height). |
| `--min-size` | `CharacterSheetCropper.min_size` | Default 128; rejects crops smaller than this many pixels. |

Unlike stages 1-3, stage 4 does not take a seed — it is purely deterministic given the input sheets. The workflow JSON is tiny (`VN_Step4_CharSpriteCreatorV5.json`: ~2.4 KB, 3 nodes):

1. `SpriteGenerator` — reads disk state, emits a list of tensors
2. `CharacterSheetCropper` — crops each tensor into per-pose sprites
3. `SaveImage` — writes the output PNGs

### Example invocations

#### Render all sprites for a character

```bash
vnccs sprite render "Aria"
```

Submits `VN_Step4_CharSpriteCreatorV5.json` with `SpriteGenerator.character = "Aria"`. The node scans `Sheets/` for every (costume, emotion) it finds and emits 12 sprites per combo. Output goes to `Sprites/<costume>/<emotion>/sprite_<emotion>_<n>.png`.

#### Render only one costume

```bash
vnccs sprite render "Aria" --costume casual
```

The wrapper patches the workflow to filter. Since `SpriteGenerator` has no costume filter built in, the cleanest path is to temporarily symlink/copy `Sheets/casual/` into a scratch character named `Aria__casual_only` before submitting. Simpler alternative the wrapper can adopt: submit the full render but delete unwanted outputs after the fact.

#### Render only the emotions you care about for a specific costume

```bash
vnccs sprite render "Aria" --costume casual --emotion happy --emotion sad
```

Same caveat as above — `SpriteGenerator` is "render everything on disk for this character". The wrapper either accepts the extra renders, or pre-trims the `Sheets/` tree.

#### Render at a lower resolution to save time

```bash
vnccs sprite render "Aria" --output-resolution 1536
```

Patches `CharacterSheetCropper.target_height`. Halving the height roughly halves the PNG size and the crop time. Quality loss is linear in the multiscale.

### Output layout

After `vnccs sprite render Aria`:

```
ComfyUI/output/VN_CharacterCreatorSuit/Aria/
  Sprites/
    casual/
      happy/
        sprite_happy_1.png  ... sprite_happy_12.png   # 12 per-pose sprites
      sad/
        sprite_sad_1.png    ... sprite_sad_12.png
      ...
    Naked/
      neutral/
        sprite_neutral_1.png ... sprite_neutral_12.png
    school/
      happy/
        ...
```

Each PNG has a transparent alpha channel (via the upstream `VNCCS_RMBG2` background removal from earlier stages — stage 4 preserves it). Sprites are full-character cutouts, ready to drop into a Ren'Py or Unity VN project.

### What the Stage 4 workflow actually does

From `VN_Step4_CharSpriteCreatorV5.json`:

1. **SpriteGenerator** (`nodes/sprite_generator.py`). `generate_sprites(character)`:
   - Walks `Sheets/` to enumerate costumes.
   - For each costume, walks emotions.
   - For each (costume, emotion), calls `utils.load_character_sheet(character, costume, emotion, with_mask=True)` to pull the highest-numbered sheet PNG as a tensor with its alpha mask.
   - Builds the target sprite path: `Sprites/<costume>/<emotion>/sprite_<emotion>_`.
   - Emits lists: `(image_tensors, file_paths, mask_tensors)`. Note that `file_paths` is extended 12 times per emotion combo — one entry per the 12 eventual per-pose sprites.
2. **CharacterSheetCropper** (`nodes/sheet_crop.py`). Takes the tensor and mask, splits the 2x6 grid into 12 sprites, uses the mask to trim transparent padding, and resizes to `target_height` (default 3072) while maintaining aspect ratio. Rejects crops smaller than `min_size` (default 128) — that's how missed-pose empty cells get filtered out.
3. **SaveImage** — writes each cropped PNG to the path from step 1 with a numeric suffix appended (`sprite_happy_1.png`, `_2.png`, ...).

## Stage 5 — LoRA Dataset Export

### Parameters

| CLI flag | Node input | Notes |
|---|---|---|
| `--character` | `DatasetGenerator.character` | |
| `--game-name` | `DatasetGenerator.game_name` | Prefix applied to the character's name in captions (e.g. `VN_Aria`). Default `VN`. |
| `--additional-caption` | `DatasetGenerator.additional_caption` | Free-form text appended to every caption. |
| `--out` | (wrapper copies the `lora_dir` to a user path) | Stage 5's raw output is always inside the VNCCS tree; the wrapper can copy it to an external target directory. |

### Example invocations

#### Export a dataset for kohya-ss

```bash
vnccs dataset export "Aria" --game-name "MyVN" --out ./datasets/aria
```

Submits `VN_Step5_LoraDataSetGeneratorV5.json`. The `DatasetGenerator` node writes image+caption pairs to `Aria/lora/`. The wrapper's `--out` flag triggers a post-run copy to `./datasets/aria/` (creating the directory if needed).

#### Preview the captions without exporting

```bash
vnccs dataset preview "Aria" --game-name "MyVN"
```

The wrapper calls `DatasetGenerator.build_caption_text` logic in-process (no ComfyUI submission needed — it's pure Python over the character config). Prints the first few caption examples so the user can sanity-check them before committing to the full export.

#### Add an extra tag to every caption

```bash
vnccs dataset export "Aria" \
  --game-name "MyVN" \
  --additional-caption "anime style, illustration" \
  --out ./datasets/aria
```

### Output layout

Inside the VNCCS tree:

```
ComfyUI/output/VN_CharacterCreatorSuit/Aria/
  lora/
    casual_happy_face_1.png        # from Faces/casual/happy/face_1.png
    casual_happy_face_1.txt        # auto-generated caption
    casual_happy_face_2.png
    casual_happy_face_2.txt
    ...
    casual_happy_sprite_1.png      # from Sprites/casual/happy/sprite_happy_1.png
    casual_happy_sprite_1.txt
    ...
    Naked_neutral_face_1.png
    ...
```

Every image has a paired `.txt` caption file. The filename pattern is `<costume>_<emotion>_<original_filename>`. That naming is intentional: Kohya-ss sorts by filename and processes images in directory order, so grouping by costume-then-emotion clusters similar samples together.

### What the captions look like

`DatasetGenerator.build_caption_text` in `nodes/dataset_generator.py` builds a comma-separated token list:

```
MyVN_Aria, 1girl, 17yo, portrait, elf, red long wavy hair, green eyes, freckles, white skin, sweatdrop, happy, elf ears silver earring, wear casual suit, simple background, green background, solid background
```

For sprite images (full-body), the template adds `multiple views, same character in different poses` AND swaps `1girl` -> `2girls` (or `1boy` -> `2boys`) to reflect the 12-pose grid that's been retained. For face images the caption uses `portrait` as the image-type token instead.

The `sweatdrop` token is hardcoded in `build_caption_text` — it's always added. That's a VNCCS convention (it's a consistent anchor token for the trained LoRA). Users who dislike it can override via `--additional-caption` and then sed-strip.

### What the Stage 5 workflow actually does

From `VN_Step5_LoraDataSetGeneratorV5.json`:

1. **DatasetGenerator** (`nodes/dataset_generator.py`). `generate_dataset(character, game_name, additional_caption)`:
   - Creates `<character>/lora/`.
   - Walks `Faces/` subtree: for each (costume, emotion) directory, copies every `face_*.png` to `lora/<costume>_<emotion>_face_N.png` and writes a matching `.txt` built from `build_caption_text(..., image_type="portrait")`.
   - Walks `Sprites/` subtree: for each (costume, emotion) directory, copies every `sprite_*.png` to `lora/<costume>_<emotion>_sprite_N.png` and writes a matching `.txt` with `image_type="full body"` and the `2girls/2boys` swap.
   - Returns the absolute `lora_dir` path.
2. **Save Text File** node — given the path, writes a receipt text file to ComfyUI output. This is cosmetic; the real work is the file copies the DatasetGenerator does as a side effect.

## Gotchas

- **Stage 4 is slow.** Each costume-emotion combo walks disk, loads tensors, crops 12 sprites, and saves. With 4 costumes x 10 emotions that's 40 combos x 12 sprites = 480 PNG writes. Expect 5-20 minutes on a warm cache. ComfyUI will appear idle (no GPU work for stage 4 beyond the mask interpolation) so progress polling will look odd — the wrapper should echo `[<n>/<total>] processing <costume>/<emotion>` based on parsing the SpriteGenerator's stdout lines.
- **Stage 4 is CPU-bound.** There is NO diffusion in stage 4. It's pure tensor slicing + cropping + PNG encoding. Running it in parallel with another diffusion job is fine, and a 16-core CPU will finish faster than a 4-core + RTX 4090.
- **No prerequisite check.** If a costume has a `Sheets/<costume>/happy/sheet_happy_*.png` but no `Faces/<costume>/happy/` (because stage 3's face crop step failed but the sheet succeeded), stage 4 still produces sprites from the sheet. Stage 5 will then be missing the face portraits for that combo. Warn during `dataset preview` if `Faces/` coverage is incomplete vs `Sheets/` coverage.
- **Empty `Sheets/` = empty output.** If stage 1 was never run for the character, `SpriteGenerator.generate_sprites` prints "Sprites folder not found" (actually the Sheets folder — the error message is misleading) and returns empty lists. The wrapper should pre-check for `Sheets/Naked/neutral/` existence and refuse to submit with exit 2.
- **Stage 5 depends on Stage 4 having written `Sprites/`.** If you run `dataset export` without running `sprite render` first, the resulting dataset has face crops only (no full-body sprites). That's a legal outcome — a portrait-only LoRA — but likely not what the user wanted. Warn if `Sprites/<character>/` doesn't exist or is empty.
- **Hardcoded `lora/` folder.** `DatasetGenerator` writes to `<character>/lora/` with a lowercase `l`, but the README says `Lora/`. Don't trust the README: the actual code (`dataset_generator.py` line ~134) uses `lora`. The wrapper's `--out` copy must source from the lowercase path.
- **`SaveImage` path interaction.** `SpriteGenerator.generate_sprites` returns file_paths like `.../Sprites/casual/happy/sprite_happy_`, then `SaveImage` appends `_00001_.png` etc. via ComfyUI's default numbering. The filename_prefix is a FULL PATH, which means it bypasses the `--output-directory` flag — stage 4 always writes inside the VNCCS tree regardless of ComfyUI's output-directory setting. If the user expects their global output dir to be respected, warn.
- **Sprite gender-swap caption bug for edge cases.** `build_caption_text` does a string `.replace("1girl", "2girls")` for full-body images. If the character's additional_details happens to contain `1girl` literally (rare but possible via `--additional-details`), that will also get double-replaced. The wrapper can normalize additional_details on character creation to avoid this.
- **Additional caption gets appended to EVERY image.** There's no per-image override. If the user wants "detailed outfit" on costume `school` only, they need to pass `--additional-caption` twice in two separate runs with different filters — or post-process the `.txt` files.
- **LoRA folder collision on re-run.** `DatasetGenerator` uses `shutil.copy2` and does not clear the target directory first. Re-running stage 5 accumulates files rather than overwriting cleanly when `<character>/lora/` already has samples from a previous game_name. The wrapper should offer `--clean` to wipe the folder before regeneration.
- **Output dir collision on `--out`.** The wrapper must check that `--out ./datasets/aria` doesn't already contain files, or warn, or accept `--force`. Otherwise the user silently merges two LoRA datasets.

## Under the Hood — interaction summary

Stage 4 and 5 are "orchestration-only" stages. They do zero neural-network inference themselves (no CLIPTextEncode, no KSampler, no VAEDecode). They are Python file-walking scripts wrapped in ComfyUI node interfaces, executed on the ComfyUI server. That's why:

- The workflow JSONs are tiny (2.4 KB and 1.1 KB vs 180+ KB for stages 1-2).
- The wrapper's progress UX has to be based on parsing stdout rather than `/queue` progress (the progress bar goes from 0 to done in one step).
- Both stages could in principle be executed by the wrapper locally (port the Python logic) instead of round-tripping through ComfyUI. For now, staying on the `/prompt` API is consistent with stages 1-3 and keeps ComfyUI as the single source of truth for the output path.

## Sources

- [VNCCS README (stage 4 + 5 sections)](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md)
- [VN_Step4_CharSpriteCreatorV5.json](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step4_CharSpriteCreatorV5.json)
- [VN_Step5_LoraDataSetGeneratorV5.json](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step5_LoraDataSetGeneratorV5.json)
- [nodes/sprite_generator.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/sprite_generator.py) — the on-disk walker.
- [nodes/dataset_generator.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/dataset_generator.py) — caption builder and file copier.
- [nodes/sheet_crop.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/sheet_crop.py) — `CharacterSheetCropper` per-pose splitter.
- [utils.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/utils.py) — `load_character_sheet`, `list_characters`, directory helpers.
- Upstream repo: <https://github.com/AHEKOT/ComfyUI_VNCCS>
- Third-party docs: <https://www.runcomfy.com/comfyui-nodes/ComfyUI_VNCCS>
