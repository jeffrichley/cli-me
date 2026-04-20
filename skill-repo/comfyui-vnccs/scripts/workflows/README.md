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
