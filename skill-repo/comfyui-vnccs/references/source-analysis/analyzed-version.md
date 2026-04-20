---
title: Analyzed Version
tags: [vnccs, version, provenance]
source: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/
date: 2026-04-20
---

# Analyzed Version

## Version

| Field | Value |
|---|---|
| Package | ComfyUI_VNCCS (Visual Novel Character Creation Suite) |
| Version analyzed | **2.1.0** (from `pyproject.toml`) |
| Git branch | `main` (from `.git/HEAD`) |
| Git commit | `7c3281f4aa16d005c89accb6d11b9aab2d92a1a1` |
| Git tag at commit | `refs/tags/2.1.0` (packed ref resolves to same SHA) |
| Short commit | `7c3281f` |
| Date analyzed | 2026-04-20 |
| License | See `LICENSE` file at repo root |
| Publisher | `vnccs` (Comfy Registry, `tool.comfy.PublisherId`) |

The `pyproject.toml` is the source of truth for the version string. The
repository-level `Changelog.md` file exists but is empty (0 bytes) in this
clone — it is a stub. Version history must be read from the git log or from
the upstream GitHub releases page; there is no in-repo changelog text.

The packed-refs file lists both `refs/tags/1.1.0` (`f2b9e79`) and
`refs/tags/2.1.0` (`7c3281f`). No `2.0.x` intermediate tag is present, which
matches how the upstream project releases majors/minors directly.

## Upstream

| Field | Value |
|---|---|
| Repository | https://github.com/AHEKOT/ComfyUI_VNCCS |
| Wiki | https://github.com/AHEKOT/ComfyUI_VNCCS/wiki (referenced from `pyproject.toml`) |
| Issues | https://github.com/AHEKOT/ComfyUI_VNCCS/issues |
| Model mirror | https://huggingface.co/MIUProject/VNCCS/tree/main (per README) |

The installed directory tracks `origin/main` — `.git/packed-refs` records
`refs/remotes/origin/main` at the same SHA as the checked-out commit, so the
install is current with upstream `main` as of the clone date
(2026-04-13).

## Installed location

| Field | Value |
|---|---|
| Install path | `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\` |
| Load mechanism | ComfyUI discovers `custom_nodes/*/` at startup; `__init__.py` exports `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` |
| Web UI directory | `web/` (declared via `WEB_DIRECTORY = "web"` in `__init__.py:10`) |
| Output directory | `ComfyUI/output/VN_CharacterCreatorSuit/` — see [`state-management.md`](state-management.md) |

VNCCS also registers aiohttp HTTP endpoints on the ComfyUI PromptServer
(`__init__.py:21-226`): `/vnccs/config`, `/vnccs/create`,
`/vnccs/create_costume`, `/vnccs/models/{filename}` (FBX for 3D pose
editor), `/vnccs/pose_presets`, `/vnccs/pose_preset/{filename}`,
`/vnccs/get_emotions`, `/vnccs/get_character_costumes`,
`/vnccs/get_character_sheet_preview`, `/vnccs/get_emotion_image`.

These endpoints are the primary way the JS front end talks to the backend.
A CLI wrapper that drives VNCCS via the REST / prompt-graph API of ComfyUI
does **not** need to hit these endpoints directly — they exist to serve the
VNCCS panel in the ComfyUI web interface. However they are convenient for
`vnccs check` / `vnccs character list` since they already enumerate the
state directory that the wrapper needs anyway.

## Python dependencies

Declared in `pyproject.toml` and `requirements.txt`:

| Package | Role |
|---|---|
| `torch` | Tensor ops; ComfyUI already pins a version |
| `numpy` | Array math |
| `Pillow` | Image I/O (PIL) |
| `opencv-python` | `cv2` — used in `sheet_crop.py`, `emotion_generator_v2.py`, `sheet_manager.py` for contour detection, mask edge smoothing, and Gaussian blur |
| `huggingface_hub` | Downloads RMBG-2.0, BEN, BEN2, INSPYRENET weights on demand (see `sheet_manager.py:11` `hf_hub_download`) |
| `timm` | **Listed in `pyproject.toml` but not in `requirements.txt`** — transitive dep of the RMBG-2.0 BiRefNet model |

The `requirements.txt` omits `timm`; the discrepancy is non-fatal because
ComfyUI's base environment usually supplies it. The skill's `models check`
command should still verify timm is importable before declaring the RMBG
stack healthy.

Additional runtime imports observed in node modules (not declared as
dependencies, expected to be provided by ComfyUI's base env):

- `transformers` (`sheet_manager.py:12` — `AutoModelForImageSegmentation`)
- `torchvision.transforms` (`sheet_manager.py:7`)
- `safetensors.torch` (optional fallback path inside `RMBGModel.load_model`)
- `transparent_background` (required by INSPYRENET only, lazy import)
- `folder_paths` (ComfyUI core)
- `comfy.utils` (ComfyUI core — used in `vnccs_qwen_encoder.py`)
- `comfy.samplers.KSampler` (ComfyUI core — queried in
  `sampler_scheduler_picker.py` to produce the runtime sampler/scheduler
  enumerations)
- `node_helpers` (ComfyUI core)
- `server.PromptServer`, `aiohttp.web` (ComfyUI core)

## Minimum ComfyUI version

`pyproject.toml` does **not** declare a minimum ComfyUI version. The
`README.md` does not declare one either. There is no `python_requires` or
`[project.requires-python]` block.

Observed hard dependencies on modern ComfyUI features:

- Subgraph workflow format with `definitions.subgraphs` block (introduced
  in ComfyUI's 2024 "subgraph" feature) — all 4 QWEN workflows
  (`VN_Step1`, `VN_Step1.1`, `VN_Step2`, `VN_Step3`) use this.
- `folder_paths.add_model_folder_path` (`sheet_manager.py:21`) — this API
  has been stable in ComfyUI for 2+ years.
- `comfy.samplers.KSampler.SAMPLERS` / `.SCHEDULERS` class attributes —
  stable.

**Practical minimum**: A ComfyUI release from mid-2024 or later is
required, because of subgraph support in the workflow format. The
installed ComfyUI at `E:/workspaces/tools/comfy/ComfyUI/` on Jeff's machine
should be treated as the reference version.

## Package layout

```
ComfyUI_VNCCS/
  __init__.py                    # HTTP endpoints + NODE_CLASS_MAPPINGS export
  utils.py                       # State helpers (paths, config, seed, age, sex, sheets)
  pyproject.toml
  requirements.txt
  LICENSE
  README.md
  Changelog.md                   # Empty (0 bytes)
  nodes/
    __init__.py                  # Aggregates mappings from each submodule
    character_creator.py         # Stage 1: Character Creator
    character_preview.py         # Stage 1 helper (no file output)
    character_selector.py        # Stage 2/3: Asset Selector (SDXL + QWEN variants)
    common_nodes.py              # Passthrough: Integer/Float/String/Multiline/PromptConcat
    dataset_generator.py         # Stage 5: LoRA dataset export
    emotion_generator.py         # Stage 3 v1: classic SDXL emotions
    emotion_generator_v2.py      # Stage 3 v2: Emotion Studio (visual grid)
    pose_generator.py            # 12-pose OpenPose grid generator
    sampler_scheduler_picker.py  # Wraps comfy.samplers.KSampler enumerations
    sheet_crop.py                # Contour-based sheet cropper
    sheet_manager.py             # Sheet split/compose + RMBG2 + ChromaKey + QuadSplitter + Resize + ColorFix + MaskExtractor
    sprite_generator.py          # Stage 4: sprite loader/paths
    vnccs_pipe.py                # Model/CLIP/VAE/Conditioning pipe object
    vnccs_qwen_encoder.py        # Qwen-Image-Edit 3-reference encoder
  pose_utils/
    skeleton_512x1536.py         # BODY_25 skeleton, 512×1536 canvas
    pose_renderer.py             # OpenPose + schematic PIL rendering
    bone_colors.py
    advanced_renderer.py
  character_template/
    CharacterSheetTemplate.png
    CharacterSheetTemplateShort.jpg
  emotions-config/
    emotions.json                # 157 emotions across 9 categories
    images/                      # Per-emotion thumbnails (PNG)
  presets/
    poses/
      vnccs_poseset.json         # Default 12-pose preset (BODY_25 joints)
  workflows/
    VN_Step1_QWEN_CharSheetGenerator_v1.json        # 181 KB
    VN_Step1.1_QWEN_Clone_Existing_Character_v1.json # 233 KB
    VN_Step2_QWEN_ClothesGenerator_v1.json          # 112 KB
    VN_Step3_QWEN_EmotionStudio_V1.json             #  43 KB
    VN_Step4_CharSpriteCreatorV5.json               #   2.4 KB
    VN_Step5_LoraDataSetGeneratorV5.json            #   1.1 KB
    V1SDXL/                                          # Legacy SDXL workflows
    old_workflows/                                   # Earlier v3/v4/v4.1 versions
  web/                                               # JS for the ComfyUI web panel
```

## Key numbers

| Metric | Value |
|---|---|
| Total custom node classes exported | **22** (see [`node-surface.md`](node-surface.md)) |
| Current workflows shipped | 6 (`VN_Step1`, `VN_Step1.1`, `VN_Step2`, `VN_Step3`, `VN_Step4`, `VN_Step5`) |
| Legacy SDXL workflows bundled | 3 (`workflows/V1SDXL/`) |
| Older deprecated workflows | 11 (`workflows/old_workflows/`) |
| Emotion presets | 157 across 9 categories (`emotions-config/emotions.json`) |
| Default pose preset | 12 poses on a 512×1536 canvas, BODY_25 joint set |
| Distinct model files referenced across current workflows | **15** (see [`required-models.md`](required-models.md)) |

## What changed between 1.1.0 and 2.1.0

With `Changelog.md` empty and no in-repo release notes, the shape of the
2.1.0 release must be inferred from the node surface and README:

- **QWEN Image Edit pipeline** — 4 of the 6 current workflows are QWEN
  variants. The `vnccs_qwen_encoder.py` module and all `fc3ddbcc-…` /
  `c6f6dc09-…` "QWEN Loader" subgraphs exist only in 2.1.0 territory.
- **Emotion Studio (V2)** — `emotion_generator_v2.py` with visual grid
  selection, while the classic `emotion_generator.py` remains as an SDXL
  fallback.
- **Pose Generator** — `pose_generator.py` with BODY_25 skeleton and an
  interactive 3D/FBX-driven web editor (FBX files served via
  `/vnccs/models/{filename}` endpoint).
- **Clone Existing Character (Step 1.1)** — new workflow that uses QWEN
  image-edit to re-draw an existing character image into the VNCCS sheet
  format.

Upstream README indicates planned future additions (Flux, NanoBanana,
consistent backgrounds, animated sprites, RenPy translation) — none of
these are shipped in 2.1.0 and are out of scope.

## Sources

- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\pyproject.toml` (version string, upstream URLs, deps)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\requirements.txt`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\README.md`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\Changelog.md` (empty)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\.git\HEAD`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\.git\packed-refs`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\__init__.py`
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\__init__.py`
- https://github.com/AHEKOT/ComfyUI_VNCCS
- https://github.com/AHEKOT/ComfyUI_VNCCS/wiki
- https://huggingface.co/MIUProject/VNCCS/tree/main
