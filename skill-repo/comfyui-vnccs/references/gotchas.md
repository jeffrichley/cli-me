# comfyui-vnccs Gotchas

Known upstream bugs, environmental footguns, and sharp edges. All verified
against VNCCS 2.1.0 at pin time (commit `7c3281f`).

## ⚠️ Stage 3 QWEN workflow is broken upstream

`VN_Step3_QWEN_EmotionStudio_V1.json` references two node class types that
are **not registered** in any published VNCCS branch:

- `VNCCS_QWEN_Detailer`
- `VNCCS_BBox_Extractor`

Confirmed by searching `main` (2.1.0), `origin/CharacterStudio`, and
`origin/cleanup` branches — these names appear only in workflow JSONs,
never in any `.py` file's `NODE_CLASS_MAPPINGS`. Even the newer v2.3
workflows in the `cleanup` branch still reference `VNCCS_BBox_Extractor`
with no Python class to back it. The upstream author appears to be
mid-refactor with the missing classes in a private dev environment.

**Mitigation in this skill:** `vnccs emotion add` defaults to `--legacy`
(uses `V1SDXL/VN_Step3_CharEmotionGeneratorV6.json` — a stable SDXL
workflow that works today). `--qwen` flag opts into the broken workflow
for when upstream ships the missing node classes.

## Sprite render has no per-costume filter

`SpriteGenerator` (stage 4) ignores any filter and renders every
(costume × emotion) combination the character has on disk. There is no
`--costume`-only flag upstream, and Jeff's explicit scope decision was
"render everything, no filter" for v0.1.

If you want selective rendering, delete un-needed costume/emotion
directories before running `sprite render`.

## Hardcoded output paths

`sprite_generator.py` and `dataset_generator.py` append
`VN_CharacterCreatorSuit/` to their output path regardless of ComfyUI's
`--output-directory` flag. The wrapper's `list` / `show` commands know
about this and look in the right place, but if you're inspecting outputs
manually, check `<comfyui-output>/VN_CharacterCreatorSuit/`.

## All QWEN workflows are GUI-format with subgraphs

Model filenames (checkpoints, LoRAs, ControlNets) live inside nested
`definitions.subgraphs[*].nodes[*].widgets_values`, NOT at top-level
nodes. The wrapper parameterizes by descending into subgraphs OR
pre-converting GUI → API format before submission to ComfyUI's `/prompt`
endpoint. The sibling `comfyui` skill's `workflow run` command handles
the conversion.

## ComfyUI has no hot-reload for custom nodes

After installing new packs or updating VNCCS, you MUST restart ComfyUI
before the wrapper's commands will succeed. The `comfyui custom-nodes`
commands print a reminder after each install/update/remove.

## COMFY_PATH must be set

Every command that reads VNCCS's state (character sheets, costumes,
emotions on disk) needs to know where ComfyUI lives. Set `COMFY_PATH`
once per shell, or pass `--path` to every command.

## `picked_variant` is wrapper-only metadata (not read by VNCCS)

The wrapper's `clothing list` (and Wave 2's planned `clothing pick`)
surface a `picked_variant` field per costume, written to
`<character>_config.json` under `costumes[<name>].picked_variant`.
**VNCCS itself does not read this key.** Upstream `utils.load_character_sheet`
always picks the file with the highest `NNNNN` sequence (greatest on
disk), ignoring any user selection.

This means:

- `clothing pick` alone does NOT change which variant subsequent stages
  (sprite render, emotion add) use. If you want the user's choice to
  actually take effect in VNCCS's pipeline, the picker must RENAME or
  RENUMBER files so the chosen variant has the highest `NNNNN` on disk.
- `clothing list`'s "Picked" column is informational — a lightweight
  wrapper-layer bookmark, not an authoritative selection.

Wave 2's `clothing pick` must either (a) implement the rename/renumber
strategy to make the choice effective, or (b) stay as wrapper-only
metadata with this limitation documented. Decision pending.

## Model footprint is large

Full VNCCS capability requires **~28 GB (QWEN-only)** to **~42-46 GB
(QWEN + SDXL + upscalers + Illustrious checkpoint)** of models. `vnccs
check models` reports what's missing with download URLs. Plan disk
accordingly.

## Illustrious checkpoint substitution

The bundled API workflows hard-code two filenames for the Illustrious
SDXL checkpoint:

- V1SDXL stack: `Illustrious/ILFlatMixV4_00001_.safetensors`
- QWEN stack:   `Illustrious/ILFlatMix.safetensors`

Neither is published anywhere we could find — they appear to be the
upstream author's local merges. The official VNCCS README explicitly
says **"Any illustrious based model"** works in the checkpoint slot.

**Mitigation:** download a popular Illustrious SDXL checkpoint
(e.g. `WAI-illustrious-SDXL` from civitai —
<https://civitai.com/models/827184/wai-illustrious-sdxl>, civitai
download API works without auth) and save it under both filenames so
either workflow's CheckpointLoaderSimple resolves. The wrapper's
download script (`tmp/vnccs_download_extras.py`) does this
automatically.

## extra_model_paths.yaml support

`vnccs check models` walks both `<COMFY_PATH>/models/` AND every
directory listed in `<COMFY_PATH>/extra_model_paths.yaml` (ComfyUI's
multi-location config mechanism), including sections marked
`is_default: true` (which apply to ANY model type, even ones not
explicitly listed in the section). Real bug found in the field where a
ComfyUI install redirected all models to `E:/data/comfy/models/`;
without honoring the YAML, the wrapper falsely reported every model
as missing. See `backend.parse_extra_model_paths`,
`backend.parse_default_base_paths`, and `backend.find_model_path`.

## Custom-node packs that DON'T honor extra_model_paths.yaml

A handful of custom-node packs register their own folder paths via
ComfyUI's `add_folder_path_and_extensions` API, with hard-coded
locations under `<COMFY_PATH>/models/<type>/`. They do NOT read
`extra_model_paths.yaml`, so models in your redirected location remain
invisible to them. Verified by source-reading at integration time:

| Pack | Folder | Affected files |
|---|---|---|
| ComfyUI-Impact-Subpack | `ultralytics/{bbox,segm}` | face_yolov8m.pt, face_yolov8m-seg_60.pt |
| ComfyUI-Impact-Pack | `sams` | sam_vit_b_01ec64.pth |
| ComfyUI_VNCCS (RMBG2 node) | `RMBG/RMBG-2.0` | model.safetensors |

**Mitigation:** physically copy these files into the canonical
`<COMFY_PATH>/models/{ultralytics,sams,RMBG}/...` location even when
`extra_model_paths.yaml` redirects everything else. The wrapper's
download script (`tmp/vnccs_download_models.py`) writes to the
extra_model_paths-mapped location for the bulk; the four affected
files need a one-time copy to canonical. Future: a `vnccs setup`
command should automate this copy.

## Live-environment prep across Wave 2 commands

Workflow widget defaults shipped by upstream don't match the current
VNCCS / ComfyUI runtime. The wrapper patches them automatically. Each
command has its own set of adjustments:

### `character create` (Step1 SDXL)

1. **`existing_character` is a dropdown of EXISTING characters.** A
   newly-named character isn't in the dropdown until VNCCS writes its
   config, so the wrapper calls `/vnccs/create?name=NAME` first.
2. **LoadImage `Character sheet` defaults to `short_body6.png`** —
   a stale leftover from the upstream author's local ComfyUI install.
   The wrapper auto-copies VNCCS's bundled `CharacterSheetTemplate.png`
   into `<COMFY_PATH>/input/` and patches the LoadImage to use it
   (unless `--pose` overrides).
3. **`VNCCS_RMBG2.background` defaults to `'Color'`** — no longer a
   valid choice (current set: Alpha/Green/Blue). Wrapper patches to
   `'Green'` so the downstream `VNCCSChromaKey` node has the right
   background to key out. `'Alpha'` would feed RGBA into a 3-channel
   conv and crash.

### `clothing add` (Step2 SDXL)

4. **Three `VNCCS_RMBG2` instances**: same `'Color' → 'Green'` patch
   needed as Step1.
5. **Orphaned `PreviewImage` node** with empty `inputs: {}` —
   ComfyUI's validator rejects it with `required_input_missing`. The
   wrapper calls `backend.prune_orphaned_output_nodes` which deletes
   any `PreviewImage`/`SaveImage` whose `images` input is missing or
   None (safe — they're UI-only, no downstream consumers).

### `character clone` (Step1.1 QWEN)

6. **LoadImage reference default is a stale hash-named `.jpg`** from
   the upstream author's environment. The wrapper auto-copies the
   source character's newest `sheet_neutral_NNNNN_.png` into
   `<COMFY_PATH>/input/` as `clone_ref_<source>.png` and patches
   the LoadImage to use it. Users can override with `--ref-image`.
7. **Three `VNCCS_RMBG2` instances**: same `'Color' → 'Green'` patch.
8. **Orphaned preview nodes**: same prune as Step2.
9. **/vnccs/create REST init**: same REST init as character create —
   the new (derived) name has to be in the CharacterCreator dropdown
   before submission.

### `clothing add` (Step2 SDXL)

10. **`costume` dropdown + `new_costume_name` both need the new name.**
    Same pattern as character create's `existing_character`:
    CharacterAssetSelector's `costume` is a dropdown populated from
    VNCCS state. `new_costume_name` ALONE doesn't trigger directory
    creation or switch the dropdown — VNCCS writes to whatever
    `costume` points to (default `Naked`), overwriting the character's
    base sheet. The wrapper calls `/vnccs/create_costume?character=X&
    costume=Y` (new `init_costume_via_rest` helper) so the dropdown
    includes Y and `Sheets/Y/neutral/` exists on disk before submission.

### `emotion add` / `sprite render` / `dataset export`

Each live-verified with no additional wrapper patches needed beyond
what was already in Wave 2. Step3/4/5 workflows don't have stale
widget defaults, no orphaned previews, no fresh dropdown constraints.

Live-verified wall clocks on a single RTX 4060 Ti (16 GB):

| Command | Workflow | Time | Output |
|---|---|---|---|
| character create | Step1 SDXL | ~13 min | 1 sheet (6144×6144, 17 MB) + 12 faces |
| clothing add (1 variant) | Step2 SDXL | ~16 min | 1 sheet + 12 faces (per variant) |
| emotion add | Step3 SDXL legacy | ~12 min | 1 sheet + 12 faces |
| sprite render | Step4 | ~7 min | 24 sprites (tall portrait, RGBA) |
| dataset export | Step5 | ~30 sec | kohya-style lora/ tree |
| character clone | Step1.1 QWEN | **fails** on 16 GB (OOM) | see below |

## Character clone OOMs on 16 GB VRAM

VNCCS 2.1.0's Step1.1 QWEN clone workflow loads:

- Qwen-Image-Edit-2511 GGUF UNet (14.4 GB on disk)
- Qwen 2.5 VL CLIP (9.4 GB)
- Qwen Lightning LoRA (0.85 GB)
- Qwen pose_helper + ClothesHelper LoRAs (~0.5 GB)
- SDXL checkpoint + IL LoRA + face detector for the refinement pass

Runtime VRAM during the refinement stage exceeds 16 GB. Observed failure
on an RTX 4060 Ti (16 GB): 27 images were saved (faces + an "Original"
reference sheet) before `torch.OutOfMemoryError` on node `637:617` —
allocation needed 644 MB while 12.75 GiB already held and 0 bytes free.

**Not a wrapper bug.** Mitigations (all require user changes):

1. Run ComfyUI with `--lowvram` or `--novram` so it offloads models
   aggressively. Slows other workflows.
2. Hardware with ≥24 GB VRAM (RTX 3090/4090/5090, A100, etc.) — the
   QWEN stack fits comfortably.
3. Swap out the Q5_0 GGUF for a smaller quantization (Q4_K_S, Q3_K_M)
   at the cost of output quality. Would require patching the bundled
   workflow to point at a different `unet_name`.

The wrapper does NOT attempt any of the above — users on small-VRAM
hardware should skip `character clone` and stick to Step1 + Step2
(SDXL), which fit comfortably in 16 GB.

## REQUIRED_MODELS list grew during integration

The original wrapper enumerated 16 required models. End-to-end
inspection of every Loader-class node across all 9 bundled API
workflows surfaced 6 more required files (DMD2 LoRA, vn_character_sheet
v4, 4x_APISR_GRL upscaler, sam_vit_b, face_yolov8m-seg) plus the
double-named Illustrious checkpoint. The expanded list is now 22
required + 1 optional — see `backend.REQUIRED_MODELS` and the audit
script `tmp/inspect_workflow_models.py`.

## pip might not be in ComfyUI's venv

If you're using `uv venv` to manage ComfyUI's Python environment, pip
isn't installed by default. The sibling `comfyui custom-nodes install`
command will fail when trying to install requirements.txt. Fix:

```bash
<comfy>/.venv/Scripts/python.exe -m ensurepip --upgrade
```

Or install `uv` globally and the wrapper (post-SWOT improvement) will
use `uv pip install --python <path>` automatically.
