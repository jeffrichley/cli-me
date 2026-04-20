# Bundled VNCCS workflows

Workflow JSONs bundled with the comfyui-vnccs skill. Pinned to a specific
upstream commit of [ComfyUI_VNCCS](https://github.com/AHEKOT/ComfyUI_VNCCS)
and SHA-256 verified at install time via a Tier 1 test.

## Provenance

| Field | Value |
|---|---|
| Upstream repo | https://github.com/AHEKOT/ComfyUI_VNCCS |
| Version pinned | **2.1.0** |
| Commit | `7c3281f4aa16d005c89accb6d11b9aab2d92a1a1` (short `7c3281f`) — "VNCCS - 2.1.0 EmotionStudio" |
| Tag | `2.1.0` |
| Date pinned | 2026-04-20 |
| License | Check upstream `LICENSE` in the VNCCS repo |

## Workflow files

### Primary pipeline (QWEN stack)

| File | SHA-256 | Size | Stage |
|---|---|---|---|
| `VN_Step1_QWEN_CharSheetGenerator_v1.json` | `441f36b87bc7b27dde8cb57ff6d8b489f2bac5ce375181d0d555c4f254387c72` | 181,220 | 1 — character sheet from prompt |
| `VN_Step1.1_QWEN_Clone_Existing_Character_v1.json` | `698bdeba5f6a3ec00d84e702264da1807c39d7d8d733a31d8587eadb1d0a5bda` | 233,577 | 1.1 — derive from reference image |
| `VN_Step2_QWEN_ClothesGenerator_v1.json` | `9e862722c13827e3936717a02f20a4bf2a662bd52943b3d11769d61c1e9b32b7` | 112,929 | 2 — clothing set |
| `VN_Step3_QWEN_EmotionStudio_V1.json` | `edb9005e6a0262a892f5e21ec37a0416819d41cf82a74a31303d3147cc3bdf73` | 43,504 | 3 — ⚠️ upstream bug (see below) |
| `VN_Step4_CharSpriteCreatorV5.json` | `175d6cc65effe55cb42eab4463e06bc57e76e2cc16c08473d71f29076a9b929b` | 2,408 | 4 — final sprite render |
| `VN_Step5_LoraDataSetGeneratorV5.json` | `94fe9e42802162c80f39d620697ddcd694e486650af70f084e42904b78c29e8f` | 1,107 | 5 — LoRA dataset export |

### V1SDXL legacy fallback (stable working path for stage 3)

| File | SHA-256 | Size | Stage |
|---|---|---|---|
| `V1SDXL/VN_Step1_CharSheetGenerator_v5.json` | `ae7f6b1a4703cde9d69ad2c998fdae9ea225ffcca2fecf1bd332d4bb69f9f31d` | 180,294 | 1 legacy |
| `V1SDXL/VN_Step2_ClothesChanger_v5.json` | `5f14e940683299fe26697c96020a4143f14ed97dd0f50523c273d23aacfb117c` | 238,933 | 2 legacy |
| `V1SDXL/VN_Step3_CharEmotionGeneratorV6.json` | `5cd87b339372247eb041a219d362325213803fbd6484cff8bd1bea586577932b` | 48,027 | **3 legacy — the default `emotion add` path** |

### API-format bundle (`api/`) — what the wrapper actually submits

The `api/` subdirectory contains API-format (`/prompt`-ready) versions of every
UI-format workflow above. Generated once-and-for-all by loading each UI workflow
into ComfyUI's web frontend and calling `app.graphToPrompt()`, which is
upstream's own UI→API conversion (`scripts/app.js`). The wrapper's submission
pipeline reads from `api/` — the top-level UI files stay as reference copies
for humans to open in the frontend.

| File | SHA-256 | Size | Nodes |
|---|---|---|---|
| `api/VN_Step1_QWEN_CharSheetGenerator_v1_api.json` | `801f831140b6a909e747d9c3b22bf6532614b3b60e170c55b18476824bbc89a9` | 52,656 | 83 |
| `api/VN_Step1.1_QWEN_Clone_Existing_Character_v1_api.json` | `3202f7aea31289638f3babcc4ad6bb936da30a224d74e522b22fc0a95b25df70` | 66,660 | 110 |
| `api/VN_Step2_QWEN_ClothesGenerator_v1_api.json` | `47c07018b9b3c0d0e4fc601e9674499ce727dc20a8f399d86b72b334cb234bd5` | 21,350 | 60 |
| `api/VN_Step3_QWEN_EmotionStudio_V1_api.json` | `fa47540e2a3ad26ba4bbf55cbec68664b7f78f0b1e17d9e49439f1af7e622040` | 5,676 | 22 (2 unresolved — see below) |
| `api/VN_Step4_CharSpriteCreatorV5_api.json` | `60b3323c8ee8300ce197b4cd71db9ec4376ea94d90ced08e9a63a38adab16d0c` | 664 | 3 |
| `api/VN_Step5_LoraDataSetGeneratorV5_api.json` | `6116805c77ba76665a93353c03192b60b2f18cf32f890cc5b11157c3a12bbe7f` | 647 | 2 |
| `api/V1SDXL/VN_Step1_CharSheetGenerator_v5_api.json` | `969e054bc06733c2540ce2050e7636e4aba419c5c1ec538ed5b7f5724d28cc4e` | 32,832 | 102 |
| `api/V1SDXL/VN_Step2_ClothesChanger_v5_api.json` | `be1c380e70569e335611f2dac99aab56112bc9f86104cc73aebc1fc65ff6419a` | 45,038 | 136 |
| `api/V1SDXL/VN_Step3_CharEmotionGeneratorV6_api.json` | `0e2aec16b0aeae1e27cd7fe6477775e7097df5ae5f28eff60052c3d19872fade` | 6,725 | 21 |

**Unresolved nodes in Step3 QWEN** — the 2 nodes shown with `"class_type": null`
in `VN_Step3_QWEN_EmotionStudio_V1_api.json` are `VNCCS_QWEN_Detailer` and
`VNCCS_BBox_Extractor`, which are unregistered in any published VNCCS branch
(documented above and in `../../references/gotchas.md`). The wrapper refuses
`--qwen` emotion generation with exit 4 until upstream ships those classes;
the legacy path (`V1SDXL/VN_Step3_CharEmotionGeneratorV6_api.json`) is the
default and is fully resolved.

**Custom nodes present at conversion time** (needed for the API files to match
the SHAs above):
ComfyUI_VNCCS, ComfyUI-Impact-Pack, ComfyUI-Impact-Subpack, ComfyUI-KJNodes,
ComfyUI-GGUF, ComfyUI-SeedVR2_VideoUpscaler, ComfyUI-Easy-Use,
comfyui_controlnet_aux, was-node-suite-comfyui, ComfyUI_UltimateSDUpscale,
rgthree-comfy.

## Stage 3 upstream-bug note (critical)

`VN_Step3_QWEN_EmotionStudio_V1.json` references two node class types that
are **not registered** in any published VNCCS branch:

- `VNCCS_QWEN_Detailer`
- `VNCCS_BBox_Extractor`

Confirmed by searching `main`, `origin/CharacterStudio`, and `origin/cleanup`
branches — the names appear only in workflow JSONs, never in any `*.py`
file's `NODE_CLASS_MAPPINGS`. Even the cleanup branch's v2.3 workflows
(newer than what's bundled here) still reference `VNCCS_BBox_Extractor`.

**Mitigation:** `vnccs emotion add` defaults to `--legacy` (uses
`V1SDXL/VN_Step3_CharEmotionGeneratorV6.json` — stable working path).
`--qwen` flag opts into the broken workflow for when upstream ships the
missing node classes.

## Verification

```bash
cd skill-repo/comfyui-vnccs/scripts/workflows
sha256sum *.json V1SDXL/*.json
```

Compare against the SHA-256 column above. Any mismatch = accidental
modification; re-download from upstream at commit `7c3281f`.

## Updating

When upstream releases a new tagged version:
1. `git -C <comfyui>/custom_nodes/ComfyUI_VNCCS pull --ff-only`
2. Re-check for the missing-node upstream bug
3. Copy updated workflow JSONs into this dir
4. Recompute SHA-256 values and update this README
5. Bump the "Version pinned" + commit fields
6. Run the full test suite (integrity tripwires will flag regressions)
