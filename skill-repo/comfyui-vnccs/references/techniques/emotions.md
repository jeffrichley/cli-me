---
title: Emotion Generation (Stage 3)
tags: [vnccs, emotions, expressions, emotion-studio, stage-3, pipeline]
sources:
  - upstream: https://github.com/AHEKOT/ComfyUI_VNCCS
  - readme: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md
  - workflow_step3: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step3_QWEN_EmotionStudio_V1.json
  - node_studio: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/emotion_generator_v2.py
  - node_legacy: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/emotion_generator.py
  - emotions_config: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/emotions-config/emotions.json
date: 2026-04-18
---

# Emotion Generation (Stage 3)

Stage 3 gives a character facial expressions. It inherits the character-and-costume state from stages 1/2 and produces face-crop "emotion sheets" per (costume x emotion) pair. Those face crops are consumed by stage 5 (LoRA dataset), and the full sheets that stage 3 also produces are consumed by stage 4 (sprite renderer) as the source of truth for a given pose+emotion+costume.

## When to use

- After at least one costume exists (use `Naked` if you don't want wardrobe variation).
- Once per emotion you want available in the VN — typically 6-15 emotions covering happy / sad / angry / surprised / neutral / and any specifics your script calls for.
- To add an emotion to a costume that was created after the first emotion pass — stage 3 is incremental; re-running only regenerates the (costume, emotion) pairs that don't already have a full `Sheets/<costume>/<emotion>/sheet_<emotion>_*.png`.

Emotions are keyed by a `safe_name` from `emotions-config/emotions.json`. There are ~200 pre-defined emotion keys spread across 8 categories: Anger, Smile, Smug, Surprise, Emotional (sad/cry), Sexual, Focus/Thought, Pain/Ailment, and Emotes (ASCII face shapes like `^_^`, `>_<`).

## The two emotion nodes

VNCCS ships two coexisting emotion paths:

| Variant | Class | Workflow | Status |
|---|---|---|---|
| **Emotion Studio (v2)** | `EmotionGeneratorV2` + frontend | `VN_Step3_QWEN_EmotionStudio_V1.json` | Current; QWEN-based; multi-costume batch. |
| **Emotion Generator (legacy)** | `EmotionGenerator` | `old_workflows/VN_Step3_CharEmotionGenerator.json` (preserved) | Deprecated per README but still works on pure-SDXL model pools. |

The wrapper defaults to Emotion Studio and exposes `--legacy` to force the SDXL variant. The legacy node accepts emotions as a free-form comma-separated STRING and generates for every costume it finds on disk in one pass (see `EmotionGenerator.generate_emotions` in `emotion_generator.py`). Emotion Studio registers aiohttp routes on the ComfyUI server (`/vnccs/get_emotions`, `/vnccs/get_character_costumes`, `/vnccs/get_character_sheet_preview`, `/vnccs/get_emotion_image`) that the wrapper can also consume directly for `emotion list` / `emotion preview` commands.

## Parameters the wrapper exposes

| CLI flag | Node input / API | Notes |
|---|---|---|
| `--character` | `character` | Must exist. |
| `--costume` | costume array in the Emotion Studio frontend | Defaults to all costumes found; one or many. |
| `--emotion` | selected emotion keys | Reference by `safe_name` (e.g. `happy`, `angry-pout`, `seductive-smile`). Repeatable. |
| `--emotion-file` | (wrapper parses file into `emotions`) | A text file of emotion safe_names, one per line. |
| `--denoise` | KSampler `denoise` on the emotion re-pass | README default 0.6; range 0.4-0.7. |
| `--seed` | KSampler `seed` | 0 = random. |
| `--prompt-style` | emotion studio dropdown | `SDXL` or `QWEN`. |
| `--legacy` | switches to `VN_Step3_CharEmotionGenerator.json` | Uses the older free-form emotion string. |

An emotion key resolves at submit time to the full token string. For `safe_name: "happy"` the Emotion Studio uses the `description` field (`"happy, smile, open_mouth, parted_lips"`) for SDXL-style prompts and the `natural_prompt` field for QWEN-style prompts. The wrapper should NEVER accept free-form emotion descriptions — always go through the JSON to ensure `safe_name` matches the folder name that downstream stages expect.

## Example CLI invocations

### Generate a "happy" emotion for a specific costume

```bash
vnccs emotion add "Aria" --costume casual --emotion happy --denoise 0.6
```

Submits `VN_Step3_QWEN_EmotionStudio_V1.json`. Output: `Faces/casual/happy/face_happy_*.png` (12 per-pose face crops) and `Sheets/casual/happy/sheet_happy_*.png` (one full 2x6 composite sheet).

### Generate multiple emotions across all costumes

```bash
vnccs emotion add "Aria" \
  --emotion happy --emotion sad --emotion angry \
  --emotion surprised --emotion neutral \
  --denoise 0.55
```

With no `--costume`, the wrapper fetches `list_costumes(Aria)` and schedules (5 emotions) x (N costumes) generations serially. For 3 costumes + `Naked`, that's 20 prompt submissions.

### Legacy SDXL path

```bash
vnccs emotion add "Aria" \
  --emotion "angry,shy,smile,pout,sad,neutral" \
  --legacy
```

The legacy node accepts a single comma-separated string and fans out to all costumes.

### Browse available emotions

```bash
vnccs emotion list                      # all 200+ keys grouped by category
vnccs emotion list --category Anger     # 19 anger variants
vnccs emotion show angry-pout           # safe_name, description, natural_prompt, emoji
vnccs emotion preview happy             # streams the preview image from /vnccs/get_emotion_image
```

`emotion list` reads `emotions-config/emotions.json` directly (or via the `/vnccs/get_emotions` HTTP route if it's up) and prints a grouped table. `emotion preview` uses the `/vnccs/get_emotion_image` endpoint.

### List what emotions exist for a character

```bash
vnccs emotion ls "Aria"                 # per-costume list of folders under Faces/<costume>/
vnccs emotion ls "Aria" --costume casual
```

This is a disk walk, not a config read — emotions exist when their folder has a successful `sheet_<emotion>_*.png`.

## Output layout

After `vnccs emotion add Aria --costume casual --emotion happy`:

```
ComfyUI/output/VN_CharacterCreatorSuit/Aria/
  Sheets/
    casual/
      neutral/sheet_neutral_1.png     # from stage 2
      happy/
        sheet_happy_1.png             # 12-pose sheet with happy face
  Faces/
    casual/
      happy/
        face_happy_1.png              # single face crop, pose 0
        face_happy_2.png              # pose 1
        ...
        face_happy_12.png             # pose 11
```

The per-pose face crops are created by the `CharacterSheetCropper` node (referenced in stage-4 workflow but also used here), which reads the 12-part grid and emits individual crops by face-detection bbox.

## Under the Hood

The Emotion Studio workflow is shorter than stage 1/2 because it uses the existing costume sheet as the starting latent (high-fidelity img2img) rather than generating from scratch.

1. **EmotionStudio frontend** (JS widget that talks to the aiohttp routes in `emotion_generator_v2.py`) — collects `character`, `costumes[]`, `emotion_keys[]`, `prompt_style`. Compiles per-combo prompt packs.
2. **Backend node (v2)** — for each (costume, emotion) combo, loads the neutral sheet via `utils.load_character_sheet(character, costume, "neutral", with_mask=True)` and the character/costume config.
3. **Prompt assembly** — the base positive prompt (character features + costume wear tokens) gets the emotion's `description` (SDXL style) or `natural_prompt` (QWEN style) appended. The `face_details` string (from `utils.build_face_details`) plus `, (<emotion_description>:1.0)` is wired to the Face Detailer node for per-pose face re-rendering.
4. **CheckpointLoader + LoRAs** — same base + VNCCS LoRAs. No new LoRA needed for emotions; the expression comes from prompt conditioning and the face-detailer denoise.
5. **ControlNet (AnytestV4)** — the neutral sheet acts as structural reference so poses stay identical; only faces are allowed to change.
6. **KSampler (low-ish denoise)** — this is the `--denoise` parameter. 0.4 = very subtle face change, 0.7 = strong expression but character drift. README default 0.6.
7. **Face Detailer** — the key emotion-rendering step. Per-pose bbox via `face_yolov8m.pt`, crop, re-diffuse with emotion-tinted positive prompt, composite back.
8. **VNCCS Sheet Manager (compose)** — stitches the 12 refined poses back into a 2x6 grid.
9. **CharacterSheetCropper** (or an equivalent split node) — writes the 12 per-pose face crops to `Faces/<costume>/<emotion>/face_<emotion>_<n>.png`.
10. **SaveImage** — writes full sheet to `Sheets/<costume>/<emotion>/sheet_<emotion>_<n>.png`.

For the **legacy path**, `EmotionGenerator.generate_emotions` in `emotion_generator.py` iterates ALL costumes it finds on disk for the given character and all emotions in the comma-separated string, so a single prompt submission can fan out to many outputs. This is convenient for "do everything" runs but harder to retry per-combo on failure.

## Gotchas

- **Unknown emotion key.** If `--emotion foo` isn't a `safe_name` in `emotions.json`, the Emotion Studio frontend would reject it visually, but the workflow JSON would just submit `foo` as a prompt token, resulting in a generic face. The wrapper MUST validate emotion keys against the JSON at parse time; exit 2 with a "did you mean `sad-emote` / `happy`?" fuzzy-match hint.
- **Denoise out of range.** 0.0 skips the face re-pass entirely (no expression change, waste of compute). 0.9+ routinely distorts the face enough to break cross-pose consistency. Hard-clamp to 0.2-0.8 in the wrapper with a warning if user exceeds 0.7.
- **Costume doesn't exist.** If `--costume black_tie` names a folder that isn't in `Sheets/`, the load step returns `None` and the legacy node silently continues to the next costume. Emotion Studio surfaces this as a frontend error; for CLI the wrapper should pre-check with `list_costumes` and fail fast with exit 2.
- **Neutral sheet missing.** Stage 3 requires `Sheets/<costume>/neutral/sheet_neutral_<n>.png`. If it's missing (e.g. someone deleted it manually), `load_character_sheet` logs "Files ... not found" and returns None. The workflow then runs on a zero-tensor and produces junk. Pre-check.
- **Only the highest-indexed sheet is used.** Same rule as stage 2: `load_character_sheet` picks the max `<n>`. If you want to emotion-generate from an older variant, either promote it (rename/renumber) or delete the newer ones first.
- **Emotion tokens are not all safe-for-work.** The `Sexual` category in `emotions.json` (~25 keys including `ahegao`, `torogao`, `in-heat`, `aroused`) will be exposed to the CLI by default. The wrapper should gate this behind the character's `nsfw` flag from stage 1 config (`character_info.nsfw`) or an explicit `--allow-nsfw` flag; otherwise omit them from `emotion list` output.
- **Emoji in safe_name.** Some keys have emoji in the display `key` field (e.g. `"smile 🙂"`) but the `safe_name` is clean (`smile`). The wrapper must use `safe_name` everywhere — folders, CLI args, file names — and treat the emoji-decorated `key` purely as display text.
- **SDXL vs QWEN prompt style.** Different style = different token list. Using `SDXL` style with a QWEN checkpoint produces weird face output. The wrapper should detect which checkpoint is actually loaded (ComfyUI `/object_info` or by inspecting the character's config style field) and auto-select the style, falling back to explicit `--prompt-style` override.
- **Per-emotion seed ignored in legacy.** The legacy `EmotionGenerator` calls `generate_seed(config_seed)` ONCE per run and reuses it across all (costume, emotion) combos. So two emotions generated in one legacy run share a seed — good for deterministic reproduction, bad for diversity. Emotion Studio iterates seeds per combo. Document this difference.
- **`emotion list` performance.** `emotions.json` is ~200 entries across 8 categories; loading it on every CLI invocation is trivial. But if the wrapper is also pulling preview images via `/vnccs/get_emotion_image`, each is a separate HTTP request — batch or lazy-fetch only on `--preview`.

## Sources

- [VNCCS README (stage 3 / Emotion Studio section)](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/README.md)
- [VN_Step3_QWEN_EmotionStudio_V1.json](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/workflows/VN_Step3_QWEN_EmotionStudio_V1.json)
- [nodes/emotion_generator_v2.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/emotion_generator_v2.py) — Emotion Studio backend + aiohttp routes.
- [nodes/emotion_generator.py](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/nodes/emotion_generator.py) — legacy generator, per-costume fan-out.
- [emotions-config/emotions.json](E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/emotions-config/emotions.json) — ~200 emotion keys with safe_name, description, natural_prompt.
- Upstream repo: <https://github.com/AHEKOT/ComfyUI_VNCCS>
- Third-party docs: <https://www.runcomfy.com/comfyui-nodes/ComfyUI_VNCCS>
