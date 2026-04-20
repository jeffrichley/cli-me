---
title: Workflow and State Model (Cross-Cutting)
tags: [vnccs, architecture, state, workflow, pipeline, cross-cutting]
sources:
  - upstream: https://github.com/AHEKOT/ComfyUI_VNCCS
  - readme: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md
  - utils: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/utils.py
  - node_selector: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/character_selector.py
  - node_creator: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/character_creator.py
  - node_sprite: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/sprite_generator.py
  - node_dataset: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/dataset_generator.py
  - node_sheetmgr: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/sheet_manager.py
  - state_mgmt: ../source-analysis/state-management.md
date: 2026-04-18
---

# Workflow and State Model

This page is for wrapper builders and readers who want to understand how the stages fit together. It covers the dependency graph, how the wrapper patches workflow JSONs before submission, how state persists between invocations, why ComfyUI must be running, and a handful of architecture-level gotchas.

## The pipeline dependency graph

```
                       +-----------------------------+
                       | stage 1                     |
                       | CharSheetGenerator (QWEN)   |
                       +-----------------------------+
                                    |
               +--------------------+--------------------+
               |                                         |
  (from scratch)                       (from reference image)
               |                                         |
               v                                         v
      +-----------------+                 +----------------------------+
      | stage 1 output  |<----------------| stage 1.1 Clone            |
      | Sheets/Naked/   |                 | VN_Step1.1_QWEN_Clone_...  |
      |   neutral/      |                 +----------------------------+
      | <name>_config   |
      +-----------------+
               |
               v
      +---------------------+
      | stage 2             |   (repeat per costume; each re-runs stage 2)
      | ClothesGenerator    |
      | Sheets/<costume>/   |
      |   neutral/          |
      | config.costumes.*   |
      +---------------------+
               |
               v
      +---------------------+
      | stage 3             |   (repeat per emotion; one combo = one pass)
      | EmotionStudio       |
      | Sheets/<costume>/   |
      |   <emotion>/        |
      | Faces/<costume>/    |
      |   <emotion>/        |
      +---------------------+
               |
               v
      +---------------------+
      | stage 4             |   (single pass; cheap vs 1-3)
      | SpriteCreator       |
      | Sprites/<costume>/  |
      |   <emotion>/        |
      +---------------------+
               |
               v
      +---------------------+
      | stage 5 (optional)  |
      | LoraDataSetGen      |
      | lora/               |
      +---------------------+
```

Forking: stage 1.1 is a drop-in replacement for stage 1 — any downstream stage treats its output identically. The wrapper should expose them as siblings (`vnccs character create` vs `vnccs character clone`) that both produce the same state-folder shape.

Fan-out: stage 2 is invoked once per costume. Stage 3 is invoked once per (costume, emotion) pair (or in a multi-costume batch if the Emotion Studio frontend is used). Stages 4 and 5 operate over the entire on-disk state in one shot.

## How the wrapper patches workflows

Every workflow JSON in `workflows/` is a **UI-format** graph (has `"nodes": [...]` and `"links": [...]`), NOT a bare API-format prompt dict. See the sibling `comfyui` skill's [workflow-formats.md](../../../comfyui/references/techniques/workflow-formats.md) for the format distinction.

The wrapper's submission flow for any stage:

1. **Load bundled JSON.** Read the packaged file (e.g. `workflows/VN_Step1_QWEN_CharSheetGenerator_v1.json`) into memory as a Python dict.
2. **Convert UI -> API.** ComfyUI's `/prompt` endpoint accepts API format. Either (a) re-export via a headful ComfyUI if the user has one, or (b) use the frontend's `graphToPrompt` logic reimplemented in Python (the sibling `comfyui` skill handles this — VNCCS wrapper composes on top of it).
3. **Patch node inputs by title.** For each VNCCS-specific node, find it by its `"properties"."Node name for S&R"` value (which matches the node class, e.g. `CharacterCreator`) or its group title (`"Transform Character Sheet to Sprites"`). Substitute widget values:
   - `CharacterCreator.new_character_name` -> wrapper's `--name`
   - `CharacterCreator.sex` -> wrapper's `--sex`
   - `CharacterAssetSelectorQWEN.character` and `.costume` -> wrapper's character/costume selection
   - `EmotionGeneratorV2` or legacy `EmotionGenerator.emotions` -> wrapper's emotion list
   - `SpriteGenerator.character` -> wrapper's `--character`
   - `DatasetGenerator.character`, `.game_name`, `.additional_caption` -> wrapper's flags
   - `KSampler.seed`, `.steps`, `.cfg`, `.denoise` -> wrapper's numerical overrides
   - `CheckpointLoaderSimple.ckpt_name` -> wrapper's `--checkpoint`
4. **Resolve image inputs.** For stage 1.1 the reference image must be uploaded via `/upload/image` first; the wrapper replaces `LoadImage.image` widget value with the returned filename.
5. **Submit to `/prompt`.** Record the returned `prompt_id`.
6. **Poll via WebSocket or `/history/{prompt_id}`.** Parse `executed` events to know when node outputs are ready. Failures come back as `execution_error` events with a `node_type` and `exception_message` — the wrapper should translate VNCCS-specific errors (missing character, missing costume, missing model) into actionable CLI messages.
7. **Collect file paths.** Because VNCCS writes via `SaveImage` into hardcoded paths (see Gotchas below), the wrapper doesn't need to do anything fancy — it just reports the expected output path based on `<character>/<stage>/<costume>/<emotion>/*.png`.

### Which fields are patched per stage

| Stage | Node(s) | Patched fields |
|---|---|---|
| 1 | `CharacterCreator`, `VNCCSPoseGenerator`, `KSampler`, `CheckpointLoaderSimple` | character attrs, pose preset, seed, steps, checkpoint |
| 1.1 | `LoadImage`, `CharacterCreator`, `KSampler` | reference image filename, character attrs, seed |
| 2 | `CharacterAssetSelectorQWEN`, `KSampler` | character, new_costume_name, slot strings, seed |
| 3 | `EmotionGeneratorV2` (or `EmotionGenerator` for legacy), `KSampler`, `Face Detailer` | character, costume(s), emotions[], denoise, seed |
| 4 | `SpriteGenerator`, `CharacterSheetCropper` | character, target_height, min_size |
| 5 | `DatasetGenerator` | character, game_name, additional_caption |

## State model — how characters persist across invocations

All stages read and write one canonical on-disk tree:

```
ComfyUI/output/VN_CharacterCreatorSuit/
  <character_name>/
    <character_name>_config.json      # single source of truth
    Sheets/<costume>/<emotion>/sheet_<emotion>_<n>.png
    Faces/<costume>/<emotion>/face_<emotion>_<n>.png
    Sprites/<costume>/<emotion>/sprite_<emotion>_<n>.png
    lora/<costume>_<emotion>_*.png + .txt
```

(Base path comes from `utils.base_output_dir()`, which calls ComfyUI's `folder_paths.get_output_directory()` + `VN_CharacterCreatorSuit`.)

### The config file

`<character_name>_config.json` is written by `CharacterCreator.create_character` in stage 1 (or the clone equivalent in stage 1.1) and augmented by `CharacterAssetSelectorQWEN.select` during stage 2. Its shape:

```json
{
  "character_info": {
    "name": "Aria",
    "background_color": "green",
    "sex": "female",
    "age": 17,
    "race": "elf",
    "aesthetics": "masterpiece,best quality,amazing quality",
    "eyes": "green",
    "hair": "red long wavy",
    "face": "freckles",
    "body": "petite",
    "skin_color": "white",
    "additional_details": "elf ears, silver earring",
    "negative_prompt": "bad quality,worst quality",
    "lora_prompt": "",
    "seed": 42
  },
  "folder_structure": {
    "main_directories": ["Sprites", "Faces", "Sheets"],
    "emotions": ["neutral"]
  },
  "character_path": "/abs/path/to/VN_CharacterCreatorSuit/Aria",
  "costumes": {
    "casual": { "face":"", "head":"", "top":"blue sweater", "bottom":"jeans", "shoes":"sneakers" },
    "school": { "head":"ribbon", "top":"sailor", "bottom":"skirt", "shoes":"loafers", "face":"" }
  },
  "config_version": "2.0"
}
```

`utils.load_config` / `utils.save_config` in `utils.py` handle reads/writes. `utils.load_character_info` is a convenience wrapper that unifies `sex` and `gender` fields (some older configs used `gender`).

### The `Sheet Manager` and `Character Selector` nodes — state enumeration

Two VNCCS nodes power the wrapper's `list` commands:

- **`VNCCSSheetManager`** (`nodes/sheet_manager.py`) — does split/compose grid ops, not really "state enumeration" despite the name. Useful to the wrapper only indirectly.
- **`CharacterAssetSelector` / `CharacterAssetSelectorQWEN`** (`nodes/character_selector.py`) — `INPUT_TYPES` walks `list_characters()` AND `list_costumes(char)` for every character every time the node is inspected. This is what populates the ComfyUI dropdowns. The wrapper can mirror this logic locally by calling `utils.list_characters()` and `utils.list_costumes(char)` directly (both are pure-Python disk reads, no ComfyUI runtime needed).

For `emotion list` the wrapper reads `emotions-config/emotions.json` directly (or hits the `/vnccs/get_emotions` aiohttp route if ComfyUI is up).

For `pose list` the wrapper reads `presets/poses/vnccs_poseset.json` directly.

## Why ComfyUI has to be running

The VNCCS skill is a **thin HTTP client** — there is no local inference. Every diffusion operation (stage 1, 2, 3) requires the ComfyUI server to be up with all required models loaded. Stages 4 and 5 are pure Python file-walking and could in theory run locally, but they're dispatched through ComfyUI for consistency.

Prerequisites the wrapper must check before ANY command that submits a prompt:

1. `curl http://localhost:8188/system_stats` — is ComfyUI up?
2. `curl http://localhost:8188/object_info` — are the VNCCS nodes registered? (If the VNCCS custom node pack isn't installed in the target ComfyUI instance, node classes like `CharacterCreator` won't exist and submission will return HTTP 400.)
3. Models check — are the required checkpoint, LoRAs, ControlNets, face-detection, SAM, upscale models present? The sibling `comfyui` skill has a `model list` command; the wrapper can delegate.

Read-only commands (`character list`, `clothing list`, `emotion list`, `dataset preview`) DO NOT need ComfyUI running — they read the state folder and config files directly. Document this clearly so users can script with cold instances.

## The hardcoded output path gotcha

**Critical.** Both `SpriteGenerator` (stage 4) and `DatasetGenerator` (stage 5) bypass ComfyUI's `--output-directory` startup flag. Evidence:

In `nodes/sprite_generator.py`:

```python
sprite_dir = os.path.join(self.base_path, character, "Sprites", costume, emotion)
os.makedirs(sprite_dir, exist_ok=True)
sprite_filename = f"sprite_{emotion}_"
sprite_path = os.path.join(sprite_dir, sprite_filename)
```

`self.base_path` is `utils.base_output_dir()`, which concatenates `folder_paths.get_output_directory() + "VN_CharacterCreatorSuit"`. So they DO respect the user's output directory... BUT they hardcode the `VN_CharacterCreatorSuit` subfolder inside it. There's no way to move the VNCCS tree elsewhere without symlinks or forking the node code.

Similarly, `nodes/dataset_generator.py`:

```python
lora_dir = os.path.join(character_path, "lora")
os.makedirs(lora_dir, exist_ok=True)
...
shutil.copy2(source_path, target_path)
```

The `lora/` directory is always inside the character's folder. You cannot direct the LoRA dataset export to an arbitrary path via the node. The wrapper's `--out` flag must do a post-run file copy from `<char>/lora/` to the user's target path.

Also: `SaveImage` nodes in stages 1-3 receive the output path as an INPUT (from the selector/creator's `sheets_path` string output), so they DO end up inside `VN_CharacterCreatorSuit`. If a user tries to rename the `VN_CharacterCreatorSuit` folder or move the character elsewhere, every subsequent stage will fail to find state. Treat the folder as immutable.

## Other architecture-level gotchas

- **The selector creates a costume entry on selection, not on generation.** When `CharacterAssetSelectorQWEN.select` runs, it calls `save_costume_info(character, costume, costume_data)` unconditionally, even if the user was just browsing in ComfyUI and never pressed "Queue". This means the config file can contain costume entries that have no corresponding `Sheets/<costume>/` directory. The wrapper can detect this divergence in `clothing list`.
- **`list_costumes` merges config and disk.** It returns the UNION of `config.costumes` keys and `Sheets/<character>/` subdirectories. Adds always include `Naked` at index 0 (it's the synthetic name for the neutral character sheet, not actually a costume).
- **Sheet filename numbering is monotonic, never reused.** Re-running stage 1 for an existing character does NOT overwrite `sheet_neutral_1.png`; it writes `sheet_neutral_2.png`. Downstream consumers use the max-index sheet. This makes A/B comparison natural (diff the old and new PNGs) but also means disk usage grows without bound over many re-rolls. Wrapper should offer `vnccs character prune "Aria" --keep-last 3`.
- **No atomicity across stages.** If stage 4 fails halfway (say, out of disk), you get a partial `Sprites/` tree. Stage 5 will happily include the partial set in the dataset. The wrapper should snapshot the `Sheets/`, `Faces/`, `Sprites/`, `lora/` manifests before each stage and expose `vnccs character status "Aria"` showing which costume-emotion combos are fully populated vs partial.
- **ComfyUI queue isolation.** Two wrapper invocations submitting for the same character simultaneously can interleave writes to `<name>_config.json`. The character_selector node does a read-modify-write without file locking. Serialize via the wrapper — treat the character's config file as a mutex.
- **State living in ComfyUI output is a cross-skill concern.** The sibling `comfyui` skill manages the ComfyUI process lifecycle. If that skill's "clean output dir" command wipes `VN_CharacterCreatorSuit/`, every character is destroyed silently. The VNCCS wrapper should register an entry in whatever "protected paths" manifest exists, or warn loudly on detection of a missing tree.

Detailed on-disk schema + config evolution lives in [../source-analysis/state-management.md](../source-analysis/state-management.md), which a sibling agent is authoring.

## Sources

- [VNCCS README](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md)
- [utils.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/utils.py) — `base_output_dir`, `character_dir`, `list_characters`, `list_costumes`, `load_config`, `save_config`, `ensure_character_structure`, `ensure_costume_structure`.
- [nodes/character_creator.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/character_creator.py) — config writer.
- [nodes/character_selector.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/character_selector.py) — costume-aware selector, dropdown population.
- [nodes/sprite_generator.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/sprite_generator.py) — hardcoded Sprites path.
- [nodes/dataset_generator.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/dataset_generator.py) — hardcoded lora/ path.
- [nodes/sheet_manager.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/sheet_manager.py) — split/compose grid helpers.
- Sibling wrapper skill: [../../../comfyui/references/techniques/workflow-formats.md](../../../comfyui/references/techniques/workflow-formats.md) — UI vs API format conversion.
- Sibling state-management doc: [../source-analysis/state-management.md](../source-analysis/state-management.md) (in-progress).
- Upstream repo: <https://github.com/AHEKOT/ComfyUI_VNCCS>
- Third-party docs: <https://www.runcomfy.com/comfyui-nodes/ComfyUI_VNCCS>
- Civitai showcase: <https://civitai.com/models/2265016/vnccs-character-creation-suite>
