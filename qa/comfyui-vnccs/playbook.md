# comfyui-vnccs Skill — QA Playbook

Per-command contracts. Phase 3 implementation agents and reviewers read
this FIRST.

VNCCS 2.1.0 pinned. Composes on top of the sibling `comfyui` cli-me skill
for workflow submission / UI→API conversion.

## 8 command groups

- [check](#check) — nodes / models / all
- [character](#character) — create / clone / list / show / prune
- [clothing](#clothing) — add / list / remove / pick
- [emotion](#emotion) — add (legacy|qwen) / list / show / preview
- [sprite](#sprite) — render
- [dataset](#dataset) — export / preview
- [pose](#pose) — list
- [config](#config) — show

Every command below documents: **signature**, **behavior**, **verification**,
**edge cases**, **error contract**.

---

## check

### `check nodes`

**Signature:** `vnccs check nodes [--path PATH]`

**Behavior:** for every pack in `backend.REQUIRED_CUSTOM_NODE_PACKS`, verify
the directory exists under `<COMFY_PATH>/custom_nodes/`. Print a table
with name + present/missing per pack. Exit 0 if all present, exit 5 if any
missing (to gate later commands).

**Verification:** stdout has a row per required pack; exit code matches.

**Edge cases:**
- COMFY_PATH unset/missing → exit 6 (`VnccsPathError`)
- Pack present but empty directory → treated as missing (no `__init__.py` or any `.py` file)

### `check models`

**Signature:** `vnccs check models [--path PATH]`

**Behavior:** cross-reference the 15 required models listed in
`references/source-analysis/required-models.md` against the actual files
on disk under `<COMFY_PATH>/models/`. Print table: model filename / model
type / target dir / present/missing / download-URL-if-missing. Exit 0 if
all present, exit 5 if any missing.

**Verification:** stdout contains all 15 model filenames; exit code matches.

**Edge cases:**
- Model present in the wrong subdir (e.g. GGUF UNet in `checkpoints/` instead of `unet/`) → reported as missing (correct location matters)
- Partial-download file (0 bytes, or < some known-good size) → reported as missing
- Optional RMBG variants missing → warn, don't fail

### `check all`

**Signature:** `vnccs check all [--path PATH]`

**Behavior:** runs `check nodes` + `check models` + server reachability.
Aggregates pass/fail into a single exit code (0 only if everything green).

---

## character

### `character create`

**Signature:**
```
vnccs character create NAME
  --description "..."
  [--pose PRESET]
  [--seed N]
  [--path PATH] [--url URL]
```

**Behavior:**
1. Validate NAME doesn't contain path separators / collide with existing character (check VNCCS's state dir)
2. Load `workflows/VN_Step1_QWEN_CharSheetGenerator_v1.json`
3. Patch parameters: character name, appearance prompt, pose selection, seed into the workflow's parameterizable nodes (see `source-analysis/workflow-stages.md` for specific node IDs)
4. Submit to ComfyUI via sibling `comfyui` skill (delegate UI→API conversion + submission)
5. Wait for completion; download character sheet image into VNCCS's output dir
6. Print `Wrote: <character_sheet_path>` on success

**Verification:** character sheet PNG lands at the expected location (per `source-analysis/state-management.md`); subsequent `character list` enumerates it.

**Edge cases:**
- NAME exists already → exit 5 unless `--force`
- Missing models (YOLO / SDXL / LoRAs) → exit 5 with `models check` hint
- ComfyUI not running → exit 2
- Workflow validation error surfaced from ComfyUI (e.g., class_type not found, required input missing) → exit 3

### `character clone`

**Signature:** `vnccs character clone NEW --from EXISTING [--prompt "..."]` plus `--pose`, `--seed`.

**Behavior:** uses stage 1.1 workflow (`VN_Step1.1_QWEN_Clone_Existing_Character_v1.json`) with reference image from `EXISTING`'s sheet. Generates a variant character.

### `character list`

**Signature:** `vnccs character list [--json]`

**Behavior:** read VNCCS's character state dir (per `source-analysis/state-management.md`) and enumerate saved characters. Rich table with name / path / costume-count / emotion-count / last-modified.

### `character show`

**Signature:** `vnccs character show NAME`

**Behavior:** inspect a character's full artifact tree: character sheet, generated costumes, emotions, whether final sprites / dataset have been produced.

### `character prune`

**Signature:** `vnccs character prune NAME --yes`

**Behavior:** recursively delete the character's entire artifact tree (sheet, costumes, emotions, sprites). `--yes` is required (no implicit confirmation) — without it, refuse with exit 3 and a message explaining the flag. Names containing `/`, `\`, `..`, `.` rejected upfront per the `custom-nodes remove` pattern.

---

## clothing

### `clothing add`

**Signature:**
```
vnccs clothing add CHARACTER
  --name COSTUME
  --description "..."
  [--variants N]    (default 4)
  [--seed N]
```

**Behavior:** validate CHARACTER exists; load `VN_Step2_QWEN_ClothesGenerator_v1.json`; patch character reference, costume prompt, variant count, seed; submit; N variant images land in VNCCS's costume state dir.

### `clothing list / remove / pick`

Standard list / delete / select-one-of-N semantics. See commands/*.py in Phase 3 for exact arg lists.

---

## emotion

### `emotion add`

**Signature:**
```
vnccs emotion add CHARACTER
  --emotion TYPE
  [--costume NAME]
  [--legacy | --qwen]
  [--denoise FLOAT]
  [--seed N]
```

**Behavior:**
- **Default `--legacy`:** load `workflows/V1SDXL/VN_Step3_CharEmotionGeneratorV6.json` (SDXL path). Works today.
- **`--qwen`:** load `workflows/VN_Step3_QWEN_EmotionStudio_V1.json`. Currently broken upstream (see `references/gotchas.md`) — exit 4 with explanation.

Patch character + costume selection, emotion type, denoise, seed. Submit. Emotion sheet lands in VNCCS's state dir.

**Verification:** emotion sheet PNG exists with expected naming convention.

**Edge cases:**
- CHARACTER / COSTUME doesn't exist → exit 5
- TYPE not in `emotions-config/` → exit 3
- `--legacy` AND `--qwen` passed together → exit 3 (mutex error)

### `emotion list / show / preview`

Standard enumerate / inspect / preview-bundled-reference-image semantics.

---

## sprite

### `sprite render`

**Signature:** `vnccs sprite render CHARACTER [--seed N]`

**Behavior:** load `VN_Step4_CharSpriteCreatorV5.json`. Render every (costume × emotion) combo on disk for CHARACTER. **No filtering** (per scope decision #2). Outputs PNGs to VNCCS's sprite dir.

**Verification:** sprite count matches len(costumes) × len(emotions); PDF-magic-style check on output (PNG magic bytes).

**Edge cases:**
- CHARACTER has no costumes → print warning, still renders base character; or exit 5 (TBD in Phase 3).
- CHARACTER has no emotions → similar.
- Render time: **minutes** per character. Use `timeout: 600000`+ for bash.

---

## dataset

### `dataset export`

**Signature:** `vnccs dataset export CHARACTER --out PATH [--game-name STR]`

**Behavior:** load `VN_Step5_LoraDataSetGeneratorV5.json`. Package sprites + captions into kohya-ss format. Output goes to `PATH`.

### `dataset preview`

Dry-run — prints what would be exported without creating files.

---

## pose

### `pose list`

**Signature:** `vnccs pose list [--json]`

**Behavior:** enumerate preset pose JSON files from `<VNCCS>/presets/poses/`. Each JSON file describes a BODY_25 skeleton pose set (stock install ships `vnccs_poseset.json` with 12 poses). Print filename + size per preset. This mirrors VNCCS's own `/vnccs/pose_presets` REST endpoint (see `__init__.py:180-199` in the node pack).

---

## config

### `config show`

**Signature:** `vnccs config show [--json]`

**Behavior:** print resolved COMFY_PATH, COMFY_URL, VNCCS install dir, bundled workflow dir (relative to this skill), detected models root, detected output dir.

---

## Cross-cutting test discipline

- Tier 1 tests (`@pytest.mark.command_graph`) mock workflow submission; assert the wrapper patches the right workflow node IDs, calls submit once, etc.
- Tier 2 tests (`@pytest.mark.integration`) use the real VNCCS install + real ComfyUI server (skip when either is unavailable via `comfy_path_or_skip` / `comfyui_running_or_skip` fixtures).
- Tier 2 generation-heavy tests (sprite render, full character create) are **optionally deferred** behind `@pytest.mark.slow` since a single sprite render takes minutes on GPU.
- Every `build_args`-equivalent function (workflow patcher) must have at least one kitchen-sink Tier 1 test that exercises every parameter (per SWOT W1).
- Every command must verify the wrapped error surfaces reach the user (per SWOT W2) — traced through the sibling `comfyui` skill's subprocess behavior if applicable.
