---
title: Clothing Sets (Stage 2)
tags: [vnccs, clothing, costume, stage-2, qwen, pipeline]
sources:
  - upstream: https://github.com/AHEKOT/ComfyUI_VNCCS
  - readme: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md
  - workflow_step2: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step2_QWEN_ClothesGenerator_v1.json
  - node_selector: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/character_selector.py
  - utils: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/utils.py
date: 2026-04-18
---

# Clothing Sets (Stage 2)

Stage 2 dresses an already-created character in one or more outfits. Each outfit becomes a named "costume" that lives under the character's state folder and is usable by every later stage (emotions, sprites, dataset).

You should already have run stage 1 (or 1.1) — stage 2 reads the `sheet_neutral_*.png` file from `Sheets/Naked/neutral/` as the anchor for clothing generation. The goal is to produce `Sheets/<COSTUME_NAME>/neutral/sheet_neutral_*.png` that looks like the same character, same 12 poses, same face, but now wearing the specified outfit.

## When to use

- Right after stage 1 to add a default outfit ("school uniform", "casual").
- Any later time to add new costumes — stages 3/4/5 will pick them up automatically because they enumerate the `Sheets/` subdirectories.
- To re-generate a specific costume with different seeds when a previous attempt looked wrong.

Skip this stage only if the character will always be naked (pure LoRA dataset for base-body training, unusual but legal).

## Parameters the wrapper exposes

The stage-2 workflow is driven by the `VNCCS Character Selector (QWEN)` node (`CharacterAssetSelectorQWEN` in `nodes/character_selector.py`). It takes these inputs:

| CLI flag | Node input | Notes |
|---|---|---|
| `--character` | `character` | Must already exist. Enumerated by `utils.list_characters()`. |
| `--name` | `new_costume_name` | The costume's on-disk folder name. Required for new costumes. |
| `--existing` | `costume` | For re-rolls; selects from `utils.list_costumes(character)`. |
| `--face` | `face` | Text: face accessory (e.g. "glasses"). |
| `--head` | `head` | Text: headwear (e.g. "cap, bow"). |
| `--top` | `top` | Text: upper body (e.g. "blue sweater"). |
| `--bottom` | `bottom` | Text: lower body (e.g. "black jeans"). |
| `--shoes` | `shoes` | Text: footwear (e.g. "white sneakers"). |
| `--description` | (split into top/bottom) | Convenience: wrapper can parse free-form into the 5 slots, or user passes them explicitly. |
| `--extra-negative` | `extra_negative_prompt` | Appended to character's base negative. |
| `--variants` | (KSampler batch_size + seed iteration) | Generate N seeds for picking the best one. |
| `--seed` | (KSampler seed) | 0 = random per variant. |

Under the hood the node ONLY stores the five slot strings (`face`, `head`, `top`, `bottom`, `shoes`) in `<name>_config.json["costumes"][<costume_name>]`. Every other parameter (character description, age, gender) is loaded from the existing config so the same character features re-generate consistently.

## Example CLI invocations

### Add a casual outfit with four variants

```bash
vnccs clothing add "Aria" \
  --name casual \
  --top "blue oversized sweater" \
  --bottom "black skinny jeans" \
  --shoes "white canvas sneakers" \
  --variants 4
```

This submits `VN_Step2_QWEN_ClothesGenerator_v1.json` four times (or once with `batch_size=4` if the workflow supports it) and writes `Sheets/casual/neutral/sheet_neutral_1.png` through `sheet_neutral_4.png`. The selector node also writes costume metadata into `Aria_config.json`.

### Add a school uniform with an accessory

```bash
vnccs clothing add "Aria" \
  --name school \
  --head "red ribbon" \
  --top "sailor uniform, white blouse, navy collar" \
  --bottom "pleated navy skirt" \
  --shoes "loafers, white knee socks" \
  --extra-negative "hat" \
  --seed 1234
```

### Re-roll an existing costume

```bash
vnccs clothing add "Aria" --existing casual --seed 77
```

Same `--name`, different seed. The selector reads the previously saved slot strings out of the config and re-generates with the new seed, overwriting (actually incrementing) `sheet_neutral_<n>.png`.

### List costumes on a character

```bash
vnccs clothing list "Aria"
```

Calls `utils.list_costumes("Aria")`, which merges `Aria_config.json["costumes"]` keys with whatever directories exist under `Sheets/` (so hand-added folders are also seen). Always returns `"Naked"` as the first entry.

### Delete a costume

```bash
vnccs clothing remove "Aria" casual
```

Deletes `Sheets/casual/`, `Faces/casual/`, `Sprites/casual/`, and pops the `costumes.casual` key from the config. No stage of VNCCS does this for you; the wrapper owns the delete operation.

## Output layout

After `vnccs clothing add Aria --name casual --variants 4`:

```
ComfyUI/output/VN_CharacterCreatorSuit/Aria/
  Aria_config.json               # now has costumes: { casual: { top:..., bottom:..., shoes:... } }
  Sheets/
    Naked/
      neutral/sheet_neutral_1.png
    casual/
      neutral/
        sheet_neutral_1.png      # variant 1
        sheet_neutral_2.png      # variant 2
        sheet_neutral_3.png      # variant 3
        sheet_neutral_4.png      # variant 4
  Faces/
    Naked/neutral/...
    casual/
      neutral/                   # empty until stage 3 runs
  Sprites/
    Naked/neutral/...
    casual/
      neutral/                   # empty until stage 4 runs
```

The `utils.ensure_costume_structure(character, costume)` call is what creates the empty `Faces/<costume>/` and `Sprites/<costume>/` directories; stage 3 and stage 4 fill them.

Only the HIGHEST-numbered `sheet_neutral_<n>.png` is used by downstream stages — `utils.load_character_sheet` sorts by the trailing index and picks the last one. To "commit" a specific variant as the canonical version, just run another generation with the same name (it will become the new highest number). To pick variant 2 when variant 4 is the newest, move/rename variants 1-3 out of the way (wrapper can surface this as `vnccs clothing pick Aria casual --variant 2`).

## Under the Hood

The stage-2 workflow is similar in shape to stage 1 but with a critical inversion: the character's neutral-naked sheet is the controlnet input, not a fresh pose set. Ordered node flow:

1. **VNCCS Character Selector QWEN** (`CharacterAssetSelectorQWEN`) — loads `<name>_config.json`, reads character_info (reconstructs the positive prompt), ensures the `costumes[<costume_name>]` entry exists, saves the five slot strings, returns `positive_prompt`, `seed`, `negative_prompt`, `face_details`, `sheet_path`, `face_path`, `character_sheet` (tensor), `costume_prompt` (newline-joined slots).
2. **LoadImage (character_sheet)** — actually supplied directly by the selector as a tensor output, no disk re-read.
3. **ControlNet chain** — the neutral sheet is preprocessed (openpose + AnytestV4) and wired into a dual ControlNet for structural lock.
4. **CheckpointLoader + LoRA stack** — same illustrious/SDXL base, plus VNCCS clothing-helper LoRA (still beta per README).
5. **CLIPTextEncode (positive)** — takes the combined character + costume prompt. The costume prompt is built by the selector: `(wear <head> on head:1.0), (wear <face> on face:1.0), (wear <top> on top:1.0), (wear <bottom> on bottom:1.0), (wear <shoes> on feet:1.0)`, each emitted only if the corresponding slot is non-empty.
6. **CLIPTextEncode (negative)** — `base_negative + (naked:2.0), (nude:2.0) + gender_negative + extra_negative_prompt`. The `(naked:2.0)` token is forced to keep the model from defaulting back to the naked reference.
7. **KSampler** — denoises from the controlnet-conditioned latent. The "match strength" described in the README is the `denoise` value here; lower denoise = more faithful to the naked sheet, higher = more creative clothing but drifts from character.
8. **Face Detailer + Upscaler + RMBG** — same as stage 1, per pose.
9. **SaveImage** — writes to `Sheets/<costume_name>/neutral/sheet_neutral_<n>.png`.

The wrapper patches the `character` COMBO widget on the selector node, the five slot strings, the `new_costume_name`, the `extra_negative_prompt`, and the KSampler's `seed` and `steps`. It does NOT need to patch the controlnet preprocessor paths; those are handled by the selector node reading the character's existing sheet.

## Gotchas

- **Character must exist.** If `--character Aria` names a character with no `Aria_config.json`, the selector node returns zero-tensors and the workflow will run but produce garbage. The wrapper should fail-fast: call `list_characters` / stat the config file before submitting. Exit 2 with a clear message.
- **Costume name collision with `Naked`.** The name `Naked` is reserved — `utils.list_costumes` always includes it first, and the naked sheet is the source-of-truth reference for stage 2. The wrapper must reject `--name Naked`.
- **Costume name collision with an existing costume.** Re-running with the same `--name` does NOT overwrite; it increments the sheet index. That's usually what you want for "A/B compare", but if the caller thinks they're replacing, they'll accumulate variants forever. Surface a `--replace` flag that deletes the old variants first.
- **Too many variants (OOM).** Each variant is a full SDXL multi-pose pass with face-detailer and upscaling. On an 8GB card, `--variants > 2` concurrent will OOM; on a 24GB card, `--variants > 8` starts to crawl. The wrapper should serialize variants through ComfyUI's queue (submit N prompts, one after the other) rather than passing a large `batch_size` to KSampler. See the sibling `comfyui` skill's queue semantics.
- **Empty slots are legal.** You can have `--top "blazer" --bottom ""` — the selector just skips the bottom wearing token. BUT if all five slots are empty the positive prompt is effectively "wear nothing", and the `(naked:2.0)` negative will fight it; the result will be chaotic. Warn if all five slot flags are blank.
- **Match strength (denoise) extremes.** The README explicitly warns: too low = character drift, too high = noise. Safe range 0.4-0.8. The wrapper should clamp `--match` to that range and warn outside it.
- **The clothing helper LoRA is beta.** README notes it "can miss some body-parts sizes — just try again with different seeds". The wrapper should surface this in the `--help` output for `clothing add` and make `--variants 4` the default (so the user gets 4 attempts without a retry loop).
- **State drift between sheet and face.** Stage 2 only regenerates the multi-pose sheet, NOT the individual face crops. The `Faces/<costume>/neutral/` folder stays empty until stage 3 runs. If a downstream consumer (stage 4 sprite render) tries to use the costume without stage 3 completing, it still works — sprites use the sheet, not face crops — but the LoRA dataset (stage 5) will be missing face-portrait samples for that costume.
- **Hand-edited costume folders are picked up but have no config entry.** If a user drops `Sheets/custom/neutral/sheet_neutral_1.png` into the tree manually, `list_costumes` surfaces it, but `Aria_config.json["costumes"]["custom"]` won't exist, so the selector node will save an empty slot dict the first time it runs on that costume. That's fine but means the costume's positive prompt has no wearing tokens. The wrapper can detect this (costume on disk but missing config entry) and surface it in `clothing list` output with a `(no metadata)` marker.

## Sources

- [VNCCS README (stage 2 section)](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md)
- [VN_Step2_QWEN_ClothesGenerator_v1.json](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step2_QWEN_ClothesGenerator_v1.json)
- [nodes/character_selector.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/character_selector.py) — both `CharacterAssetSelector` (SDXL) and `CharacterAssetSelectorQWEN`.
- [utils.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/utils.py) — `list_costumes`, `ensure_costume_structure`, `load_costume_info`, `save_costume_info`, `load_character_sheet`.
- Upstream repo: <https://github.com/AHEKOT/ComfyUI_VNCCS>
- Third-party docs: <https://www.runcomfy.com/comfyui-nodes/ComfyUI_VNCCS>
