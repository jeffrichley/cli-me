---
title: Required Models
tags: [vnccs, models, checkpoints, loras, controlnet, yolo, sam, upscalers, rmbg]
source: VNCCS workflows + sheet_manager.py + README.md
date: 2026-04-20
---

# Required Models

Complete inventory of every model file VNCCS 2.1.0 references across its
six workflows, plus the on-demand models downloaded at runtime by the
RMBG2 node. The wrapper's `vnccs models check` command should probe for
each of these and emit install hints for missing ones.

**Total explicitly-referenced model files**: 15 across the six current
workflows. Plus 4-6 on-demand RMBG/BEN/INSPYRENET variants downloaded
lazily from Hugging Face to `models/RMBG/`.

## Directory map

All paths are relative to ComfyUI's `models/` directory (`models_dir` in
`folder_paths`). Backslashes in path strings are Windows-style because
the workflows were authored on Windows; ComfyUI treats them as subdir
separators.

| ComfyUI directory | Model types |
|---|---|
| `models/checkpoints/` | SDXL checkpoints |
| `models/loras/` | All LoRAs (SDXL + QWEN) |
| `models/controlnet/` | ControlNet SDXL models |
| `models/unet/` | QWEN GGUF UNet |
| `models/clip/` | QWEN text/vision encoder |
| `models/vae/` | Image VAE (QWEN + SeedVR2) |
| `models/ultralytics/bbox/` | YOLO bbox detectors |
| `models/ultralytics/segm/` | YOLO segmentation (per README) |
| `models/sams/` | Segment Anything checkpoints (per README, but no workflow references SAM in 2.1.0) |
| `models/upscale_models/` | ESRGAN-style upscalers |
| `models/seedvr2/` or `models/diffusion_models/` | SeedVR2 DiT + VAE |
| `models/RMBG/` | RMBG-2.0, BEN, BEN2, INSPYRENET (auto-downloaded) |

## Model-by-model inventory

### 1. `qwen-image-edit-2511-Q5_0.gguf`

- **Type**: UNet (GGUF-quantized Qwen-Image-Edit 2511)
- **ComfyUI directory**: `models/unet/` (loaded via `UnetLoaderGGUF`)
- **Approx size**: ~11-13 GB (Q5_0 quantization of a ~20 GB model)
- **Used in stages**: 1, 1.1, 2, 3
- **Where to download**: https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF (2511 variant) or https://huggingface.co/QuantStack/Qwen-Image-Edit-GGUF. Upstream model: https://huggingface.co/Qwen/Qwen-Image-Edit
- **Notes**: Requires the ComfyUI-GGUF custom node (`UnetLoaderGGUF` is not a core node). The wrapper's `vnccs check` should verify this custom node is installed.

### 2. `qwen\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`

- **Type**: LoRA (speed-up "Lightning" 4-step LoRA for Qwen-Image-Edit)
- **ComfyUI directory**: `models/loras/qwen/`
- **Approx size**: ~1-2 GB
- **Used in stages**: 1, 1.1, 2, 3
- **Where to download**: https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning (the canonical Lightning-LoRA repo for Qwen-Image-Edit 2511).
- **Strength in workflows**: 1.0.

### 3. `qwen_2.5_vl_7b_fp8_scaled.safetensors`

- **Type**: CLIP / vision-language encoder (Qwen 2.5 VL 7B at FP8)
- **ComfyUI directory**: `models/clip/` (loaded via `CLIPLoader` with type `qwen_image`)
- **Approx size**: ~8 GB
- **Used in stages**: 1, 1.1, 2, 3
- **Where to download**: https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors (the workflows embed this URL literally in their JSON).
- **Notes**: This URL is present inside the workflow JSON as a `tooltip` or download hint string.

### 4. `qwen_image_vae.safetensors`

- **Type**: VAE for Qwen-Image
- **ComfyUI directory**: `models/vae/`
- **Approx size**: ~400 MB
- **Used in stages**: 1, 1.1, 2, 3
- **Where to download**: https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors

### 5. `Illustrious\ILFlatMix.safetensors`

- **Type**: Stable Diffusion XL checkpoint ("Illustrious-based model" per README)
- **ComfyUI directory**: `models/checkpoints/Illustrious/`
- **Approx size**: ~6.5 GB
- **Used in stages**: 1, 1.1 (via `CheckpointLoaderSimple` inside the `SDXL Loader` subgraph)
- **Where to download**: Civitai — search for "Illustrious" checkpoints (the `ILFlatMix` variant or any Illustrious-based SDXL checkpoint). README states: "Any illustrious based model. Should work on any SDXL model, but not tested."
- **Notes**: The wrapper should let the user substitute their preferred SDXL checkpoint since the README explicitly says any illustrious-based model works.

### 6. `IL\mimimeter.safetensors`

- **Type**: LoRA (SDXL/Illustrious style)
- **ComfyUI directory**: `models/loras/IL/`
- **Approx size**: ~200-400 MB
- **Used in stages**: 1, 1.1 (via `SDXL Core` subgraph `LoraLoader`, strength 1.0)
- **Where to download**: Civitai — search for "mimimeter LoRA"; also listed on the author's HF mirror https://huggingface.co/MIUProject/VNCCS/tree/main (README line 68).

### 7. `SDXL\AnytestV4.safetensors`

- **Type**: ControlNet (SDXL, general-purpose tile/edge detection)
- **ComfyUI directory**: `models/controlnet/SDXL/`
- **Approx size**: ~2.5 GB
- **Used in stages**: 1 only (Stage 1.1 does not use SDXL ControlNet; it goes QWEN-only)
- **Where to download**: Civitai — "AnytestV4 ControlNet SDXL". Also on the VNCCS HF mirror.

### 8. `SDXL\IllustriousXL_openpose.safetensors`

- **Type**: ControlNet (SDXL, OpenPose)
- **ComfyUI directory**: `models/controlnet/SDXL/`
- **Approx size**: ~2.5 GB
- **Used in stages**: 1 only
- **Where to download**: Civitai — "IllustriousXL OpenPose ControlNet"; also on the VNCCS HF mirror.

### 9. `qwen\VNCCS\poser_helper_v2_000004200.safetensors`

- **Type**: LoRA (VNCCS proprietary — Qwen pose helper)
- **ComfyUI directory**: `models/loras/qwen/VNCCS/`
- **Approx size**: ~200-500 MB
- **Used in stages**: 1, 1.1 (via `Pose Generation` subgraph, strength 0.5)
- **Where to download**: https://huggingface.co/MIUProject/VNCCS/tree/main (the author's official model mirror). File name: `poser_helper_v2_000004200.safetensors`.

### 10. `qwen\VNCCS\ClothesHelperUltimateV1_000005100.safetensors`

- **Type**: LoRA (VNCCS proprietary — clothing / nudify helper)
- **ComfyUI directory**: `models/loras/qwen/VNCCS/`
- **Approx size**: ~200-500 MB
- **Used in stages**: 1.1 (Remove Clothes subgraph, strength 1.65), 2 (Clothes Generator subgraph, strength 1.65)
- **Where to download**: https://huggingface.co/MIUProject/VNCCS/tree/main

### 11. `qwen\VNCCS\TransferClothes_000006700.safetensors`

- **Type**: LoRA (VNCCS proprietary — clothing transfer across poses)
- **ComfyUI directory**: `models/loras/qwen/VNCCS/`
- **Approx size**: ~200-500 MB
- **Used in stages**: 2 (Clothes replicator subgraph, strength 1.15)
- **Where to download**: https://huggingface.co/MIUProject/VNCCS/tree/main

### 12. `qwen\VNCCS\EmotionCoreV1_000003000.safetensors`

- **Type**: LoRA (VNCCS proprietary — emotion / face-detail)
- **ComfyUI directory**: `models/loras/qwen/VNCCS/`
- **Approx size**: ~200-500 MB
- **Used in stages**: 3 (QWEN Detailer subgraph, strength 1.0)
- **Where to download**: https://huggingface.co/MIUProject/VNCCS/tree/main

### 13. `bbox/face_yolov8m.pt`

- **Type**: YOLO v8m face detector (bbox, not segmentation)
- **ComfyUI directory**: `models/ultralytics/bbox/`
- **Approx size**: ~50 MB
- **Used in stages**: 1, 1.1, 3 (multiple `UltralyticsDetectorProvider` nodes)
- **Where to download**: https://huggingface.co/Bingsu/adetailer/blob/main/face_yolov8m.pt or any adetailer mirror. Also on the VNCCS HF mirror.
- **Notes**: Requires the ComfyUI Impact Pack (`UltralyticsDetectorProvider` is from that pack, not from VNCCS).

### 14. `2x_APISR_RRDB_GAN_generator.pth`

- **Type**: ESRGAN-style upscaler (anime-tuned 2x APISR)
- **ComfyUI directory**: `models/upscale_models/`
- **Approx size**: ~70 MB
- **Used in stages**: 1 only (Character Generation subgraph `UpscaleModelLoader`)
- **Where to download**: https://github.com/Kiteretsu77/APISR/releases (official releases; grab `2x_APISR_RRDB_GAN_generator.pth`). ONNX mirror: https://huggingface.co/Xenova/2x_APISR_RRDB_GAN_generator-onnx

### 15. `seedvr2_ema_3b_fp16.safetensors` + `ema_vae_fp16.safetensors`

- **Type**: SeedVR2 Video Upscaler (DiT model + matched VAE) — used here for still-image upscaling
- **ComfyUI directory**: typically `models/diffusion_models/` or a custom `models/seedvr2/` folder (depends on the SeedVR2 custom node's conventions)
- **Approx size**: DiT ~6 GB (3B params at FP16), VAE ~300 MB
- **Used in stages**: 1, 1.1, 2 (multiple Upscaler subgraphs)
- **Where to download**: https://huggingface.co/numz/SeedVR2_comfyUI (DiT + VAE weights packaged for the ComfyUI-SeedVR2 node pack).
- **Notes**: Requires the SeedVR2 custom node pack (`SeedVR2LoadDiTModel`, `SeedVR2LoadVAEModel`, `SeedVR2VideoUpscaler`). `vnccs check` should verify.

## RMBG-family models (auto-downloaded)

The `VNCCS_RMBG2` node (`sheet_manager.py:1129`) downloads these from
Hugging Face on first use via `hf_hub_download()` to `models/RMBG/{name}/`.
The user does **not** need to pre-install them — they arrive lazily. But
`vnccs check` can pre-fetch them to avoid first-run hangs.

| Model | repo_id | Files | Subdir |
|---|---|---|---|
| `RMBG-2.0` | `1038lab/RMBG-2.0` | `config.json`, `model.safetensors`, `birefnet.py`, `BiRefNet_config.py` | `RMBG/RMBG-2.0/` |
| `INSPYRENET` | `1038lab/inspyrenet` | `inspyrenet.safetensors` | `RMBG/INSPYRENET/` |
| `BEN` | `1038lab/BEN` | `model.py`, `BEN_Base.pth` | `RMBG/BEN/` |
| `BEN2` | `1038lab/BEN2` | `BEN2_Base.pth`, `BEN2.py` | `RMBG/BEN2/` |

The default in every workflow is `RMBG-2.0`, so at minimum the BiRefNet
pair (~700 MB + ~4 MB + small `.py` files) must be downloadable. BEN
variants require the `transparent_background` Python package, but it is
only imported inside the INSPYRENET code path, so BEN/BEN2/INSPYRENET are
optional unless the workflow explicitly switches to them.

## Required custom-node packs (not VNCCS itself)

VNCCS workflows depend on these external custom-node packs being
installed in ComfyUI. Missing any of them will fail workflow validation:

| Custom node pack | Used for | Where |
|---|---|---|
| **ComfyUI-Impact-Pack** | `UltralyticsDetectorProvider`, `FaceDetailer` | https://github.com/ltdrdata/ComfyUI-Impact-Pack |
| **ComfyUI-GGUF** | `UnetLoaderGGUF` | https://github.com/city96/ComfyUI-GGUF |
| **ComfyUI-SeedVR2** (or SeedVR2_VideoUpscaler) | `SeedVR2LoadDiTModel`, `SeedVR2LoadVAEModel`, `SeedVR2VideoUpscaler` | https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler |
| **rgthree-comfy** | `Lora Loader Stack (rgthree)`, `Image Comparer (rgthree)`, `Fast Groups Bypasser (rgthree)`, `Reroute` (advanced) | https://github.com/rgthree/rgthree-comfy |
| **ComfyUI-easy-use** | `easy cleanGpuUsed` | https://github.com/yolain/ComfyUI-Easy-Use |
| **ComfyUI-ControlNet AUX** | `AIO_Preprocessor`, `DepthAnythingV2Preprocessor` | https://github.com/Fannovel16/comfyui_controlnet_aux |
| **Save Text File (or equivalent)** | `Save Text File` node in Stage 5 | A number of ComfyUI packs provide this; see https://github.com/WASasquatch/was-node-suite-comfyui |
| **ComfyUI-UltimateSDUpscale** | `UltimateSDUpscale` | https://github.com/ssitu/ComfyUI_UltimateSDUpscale |

### Additional missing nodes referenced in Stage 3

The Stage 3 workflow's `QWEN Detailer` subgraph references two node
types that are not in any currently-shipping pack (including VNCCS
itself):

- `VNCCS_QWEN_Detailer`
- `VNCCS_BBox_Extractor`

These may be in a future VNCCS release or in a companion pack the author
has not yet published. Stage 3 will fail to load without them. The
wrapper should detect this at `vnccs check` time and guide the user to
use the legacy SDXL Emotion workflow
(`workflows/V1SDXL/VN_Step3_CharEmotionGeneratorV6.json`) as a fallback.

## Models from README but unused in 2.1.0 workflows

The README (lines 36-68) lists several models as "required" that do not
appear in the 2.1.0 QWEN workflows. These are likely carried over from
the SDXL-era workflows (in `V1SDXL/` and `old_workflows/`):

- `vn_character_sheet_v4.safetensors` (LoRA)
- `vn_character_sheet.safetensors` (LoRA)
- `DMD2/dmd2_sdxl_4step_lora_fp16.safetensors` (LoRA — DMD2 4-step speedup)
- `bbox/face_yolov9c.pt` (YOLO v9c — newer bbox detector)
- `segm/face_yolov8m-seg_60.pt` (YOLO v8m segmentation — alternative to bbox)
- `sam_vit_b_01ec64.pth` (SAM ViT-B segmentation model, ~375 MB)

The MVP wrapper can skip these. If the user opts into legacy SDXL
workflows (out of MVP scope), then `vnccs models check --legacy` could
probe for them.

## Storage budget summary

Approximate disk footprint for a minimal 2.1.0 QWEN-only install:

| Category | Models | Approx total |
|---|---|---|
| Qwen-Image-Edit stack | GGUF UNet + Lightning LoRA + qwen 2.5 VL CLIP + qwen VAE | ~22-25 GB |
| VNCCS LoRA pack | poser_helper + ClothesHelper + TransferClothes + EmotionCore | ~1-2 GB |
| Illustrious SDXL | ILFlatMix checkpoint + mimimeter LoRA | ~7 GB |
| SDXL ControlNet | AnytestV4 + IllustriousXL_openpose | ~5 GB |
| Upscalers | 2x APISR + SeedVR2 DiT + SeedVR2 VAE | ~6.5 GB |
| Face detector | face_yolov8m.pt | ~50 MB |
| RMBG (lazy) | BiRefNet | ~700 MB |
| **Total (minimum)** | | **~42-46 GB** |

If the user has only the QWEN-only subset (skipping Stage 1 and using
only Stage 1.1 + Stage 2 + Stage 3 via QWEN image-edit), the SDXL
checkpoint + ControlNet + APISR can be skipped, saving ~14 GB. Stage 1
(fresh character creation) requires SDXL, so `vnccs models check` should
emit targeted hints:

- `vnccs models check --stage 1` → full list
- `vnccs models check --stage 2` → QWEN subset only
- `vnccs models check --stage 3` → QWEN subset + EmotionCore + bbox/face_yolov8m

## Cross-references

- Which workflow uses which models → [`workflow-stages.md`](workflow-stages.md)
- Which node loads the model → [`node-surface.md`](node-surface.md)
- Where VNCCS stores generated output (not the model files) → [`state-management.md`](state-management.md)

## Sources

- Six workflow JSONs under `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\workflows\` (model filenames extracted via path regex and via inspecting each `definitions.subgraphs[].nodes[]`)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\sheet_manager.py` (RMBG / BEN / INSPYRENET `AVAILABLE_MODELS` dict, line 646)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\README.md` (lines 36-68 — canonical "Required Models" list)
- https://huggingface.co/MIUProject/VNCCS/tree/main (official VNCCS LoRA + aux model mirror)
- https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI (qwen CLIP + VAE, URLs embedded in the workflow JSONs)
- https://huggingface.co/Qwen/Qwen-Image-Edit (upstream Qwen-Image-Edit model)
- https://github.com/city96/ComfyUI-GGUF (UnetLoaderGGUF custom node)
- https://github.com/ltdrdata/ComfyUI-Impact-Pack (UltralyticsDetectorProvider, FaceDetailer)
- https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler (SeedVR2 nodes)
- https://github.com/Kiteretsu77/APISR (APISR upscaler)
- https://huggingface.co/Bingsu/adetailer (face_yolov8m.pt)
- https://huggingface.co/1038lab/RMBG-2.0 (RMBG-2.0 BiRefNet)
- https://huggingface.co/1038lab/BEN
- https://huggingface.co/1038lab/BEN2
- https://huggingface.co/1038lab/inspyrenet
- https://civitai.com (Illustrious checkpoint, mimimeter LoRA, AnytestV4 ControlNet, IllustriousXL_openpose ControlNet)
