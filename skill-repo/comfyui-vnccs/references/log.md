# comfyui-vnccs Skill Build Log

Append-only. Newest entries at the bottom.

---

**2026-04-20** — Phase 1 + 2 complete. VNCCS 2.1.0 pinned at commit `7c3281f`.

- **Phase 1 research:** 5 source-analysis pages (1914 lines) + 5 technique pages (974 lines) written from the installed VNCCS at `E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS`. No separate git clone — source is the installed pack.
- **Critical upstream bug found:** Stage 3 QWEN workflow references `VNCCS_QWEN_Detailer` and `VNCCS_BBox_Extractor` node classes that do NOT exist in any VNCCS branch's Python (searched `main`, `origin/CharacterStudio`, `origin/cleanup`). Even the newer v2.3 workflows in the `cleanup` branch still reference `VNCCS_BBox_Extractor` with no corresponding Python class. Decision: Stage 3 defaults to `--legacy` (uses the working V1SDXL emotion workflow); `--qwen` opts into the broken path for when upstream fixes it.
- **7 external custom-node packs installed** via the sibling `comfyui custom-nodes install` command: Impact-Pack, GGUF, SeedVR2_VideoUpscaler, Easy-Use, controlnet_aux, was-node-suite, UltimateSDUpscale. rgthree-comfy was already present.
- **Pip-bootstrap gotcha found:** Jeff's ComfyUI `.venv` is uv-managed and doesn't ship pip by default. Had to `python -m ensurepip --upgrade` manually. Logged as a SWOT item for the sibling `comfyui` skill's `custom-nodes install` command (should fall back to `uv pip install --python <path>` when uv is available).
- **Phase 2 scaffold:** SKILL.md + pyproject.toml + package skeleton + 8 dispatch stubs + 6 workflow JSONs + V1SDXL fallback + wiki operational files. Registry entry + R2 review pending.

Scope decisions locked:
1. Stage 3: `--legacy` default (SDXL), `--qwen` opt-in.
2. Sprite render: no per-costume filter, render everything.
3. Workflow conversion: delegate to sibling `comfyui` skill.
4. VNCCS pinned at `main` 2.1.0 commit `7c3281f`.

---

**2026-04-21** — Phase 3 complete (Wave 1 + 2 + 3) + integration audit.

- **Phase 3.0** shipped (`c5da949`): `load_api_workflow`, `patch_workflow_node`,
  `submit_workflow`, `wait_for_prompt` in backend.py. UI-format rejection,
  exit-code mapping (2/3/4), monkeypatchable poll interval. 24 Tier-1 tests.
- **Wave 2 submission commands** shipped (`4dde178`): character create/clone,
  clothing add (variants loop with deterministic seed sequence), emotion add
  (`--legacy` default, `--qwen` refuses with exit 4), sprite render, dataset
  export with post-completion lora/ copy. 25 Tier-1 mocked tests.
- **Wave 3 destructive commands** shipped (`b1b7456`): character prune,
  clothing remove (protects `Naked` base), clothing pick. Path-traversal
  safe — test-first caught a bug where `Path.relative_to()` without
  `.resolve()` allowed `character=".."` to escape the state root. Fixed via
  `.resolve()`-then-parent comparison. 19 Tier-1 tests.
- **Integration audit (live ComfyUI, training done):**
  - 11/11 custom-node packs registered with running server (incl. Impact-Subpack
    and KJNodes added during Phase 2 review).
  - 46/46 wiki URLs return HTTP 200; 0 broken links / orphan files.
  - All 55 Tier-2 integration tests pass.
  - **Bug fixed (`4e6c63e`)**: `check models` now honors
    `extra_model_paths.yaml`. User's install redirects models to
    `E:/data/comfy/models/`; the wrapper was probing `<COMFY_PATH>/models/`
    only and falsely reported every model as missing. New helpers
    `parse_extra_model_paths` + `find_model_path` + 13 tests.
  - **REQUIRED_MODELS list grew from 16 → 22**: end-to-end inspection of all
    Loader-class nodes across the 9 bundled API workflows surfaced 6 more
    required files (DMD2 LoRA, vn_character_sheet_v4, 4x_APISR_GRL upscaler,
    sam_vit_b, face_yolov8m-seg_60, plus the doubly-named Illustrious
    checkpoint). Audit script: `tmp/inspect_workflow_models.py`.
  - **Illustrious checkpoint substitution**: workflows hard-code
    `ILFlatMixV4_00001_.safetensors` (V1SDXL) and `ILFlatMix.safetensors`
    (QWEN), neither published anywhere. README says "any illustrious model"
    works — substituted `WAI-illustrious-SDXL` from civitai (download API
    works without auth, but use httpx — urllib's redirect handling drops
    the Cloudflare R2 signed URL).
  - **face_yolov8m-seg_60.pt**: not in Bingsu/adetailer despite being the
    natural-seeming source; lives at `24xx/segm` instead.

Test totals at end of session: 259 passing, 1 skipped.

Pending after model downloads complete:
- Live Wave 2 smoke test via `tmp/vnccs_live_test.py`
- Phase 3.5 R5 wiki execution (currently deferred while validating models)

---

**2026-04-21 (later same session)** — All 23 models downloaded + live
end-to-end verified.

Model acquisition (~46 GB total):
- 16 main + 1 optional via `tmp/vnccs_download_models.py` (HuggingFace
  repos: MIUProject/VNCCS for 8, Comfy-Org/Qwen-Image_ComfyUI for 2,
  unsloth/lightx2v/Bingsu/numz/1038lab for the rest).
- 5 missing-from-original-list models discovered by audit + downloaded
  via `tmp/vnccs_download_extras.py`: DMD2 LoRA, vn_character_sheet_v4,
  4x_APISR_GRL upscaler, sam_vit_b, face_yolov8m-seg_60.
- `face_yolov8m-seg_60.pt` is on `24xx/segm`, NOT `Bingsu/adetailer`
  (despite naming suggesting otherwise — initial 404 was the giveaway).
- Civitai WAI-illustrious-SDXL v16 (6.94 GB) used as the Illustrious
  checkpoint substitute under both filenames the workflows reference.
  Civitai signed-URL redirect requires httpx (urllib gets 403 from
  Cloudflare R2). Saved to both ILFlatMixV4_00001_.safetensors AND
  ILFlatMix.safetensors.

Wrapper bug-fix from is_default semantics: `extra_model_paths.yaml`
sections marked `is_default: true` apply to ANY model type even ones
not explicitly listed. Without this fallback, ultralytics/sams models
in the redirected location were falsely reported missing. Fix:
`backend.parse_default_base_paths` + extended `find_model_path`.

Live integration findings (4 wrapper bugs caught, all fixed):

1. CharacterCreator's `existing_character` is a runtime dropdown — the
   wrapper must call `/vnccs/create?name=NAME` first to register the
   name before submission.
2. LoadImage 'Character sheet' default `short_body6.png` is a stale
   upstream-author reference; VNCCS bundles `CharacterSheetTemplate.png`
   and the wrapper now auto-copies it into `<COMFY_PATH>/input/`.
3. VNCCS_RMBG2 default `background='Color'` is no longer valid; patch
   to `'Green'` so downstream VNCCSChromaKey works.
4. Impact-Subpack ultralytics, Impact-Pack SAMLoader, and VNCCS_RMBG2
   bypass `extra_model_paths.yaml` and require physical files at
   canonical `<COMFY_PATH>/models/{ultralytics,sams,RMBG}/` location.
   Documented; future `vnccs setup` command will automate the copy.

End-to-end live verification (Step1 SDXL on real GPU):
- live_test_002 (manual orchestration): SUCCESS in 766s, 1 sheet
  (6144×6144 RGBA, 17 MB) + 12 face crops in correct character dir.
- live_test_003 (via `vnccs character create` CLI, fully wrapper-driven):
  SUCCESS in 766s, identical output structure.
- `vnccs character list` + `vnccs character show live_test_003`
  correctly reflect live state.

Commits this round: `27cd1d8` (REQUIRED_MODELS expanded to 22),
`4eaa989` (is_default fallback), `4888971` (live-env prep in
character_create), `9b5b6b5` (gotchas update).

Test totals: 268 passing, 1 skipped.

Wave 2 commands not yet live-verified (mocked tests pass; same
live-env prep pattern likely needed for each):
- character_clone (Step1.1 QWEN — different LoadImage / RMBG defaults?)
- clothing_add (Step2 SDXL — same RMBG2 issue likely)
- emotion_add (Step3 SDXL legacy)
- sprite_render (Step4 — minimal, may just need /vnccs/create-style init)
- dataset_export (Step5 — minimal)

---

**2026-04-21 (final)** — All 6 Wave 2 commands live-tested.

Verified on live GPU (RTX 4060 Ti 16 GB):

- **character create** (Step1 SDXL): verified earlier, 13 min.
- **emotion add** (Step3 SDXL legacy): verified, 12 min. Produced
  `Sheets/Naked/happy/sheet_happy__00001.png` + 12 face crops under
  `Faces/Naked/happy/`. No wrapper patches needed beyond Wave 2 — the
  workflow's default `EmotionGeneratorV2` inputs work as-is.
- **sprite render** (Step4): verified, 7 min. Produced 24 individual
  portrait-aspect sprites under `Sprites/Naked/{neutral,happy}/` —
  one 6144×6144 reference sheet (00001) plus 12 individual ~600-900×
  2800 RGBA PNGs (00002+) per (costume, emotion) combo.
- **dataset export** (Step5): verified, ~30s (lightweight). Populated
  `lora/` with `Naked_{emotion}_{face,sprite}_NNNNN.{png,txt}` pairs —
  the kohya-style training dataset.
- **clothing add** (Step2 SDXL): verified after one fix round.
  First attempt (pre-fix) wrote outputs to `Sheets/Naked/neutral/`
  instead of `Sheets/school/neutral/` — a SILENT bug (status=success
  but wrong target dir). Root cause: `CharacterAssetSelector.costume`
  is a live dropdown like CharacterCreator.existing_character;
  `new_costume_name` alone doesn't register the name. Fix: new
  `backend.init_costume_via_rest` helper calls `/vnccs/create_costume`
  before submission; also patch `costume` to the new name (not just
  `new_costume_name`). Second attempt (81f2ee88) wrote to
  `Sheets/school/neutral/sheet_neutral_00001_.png` — correct.
- **character clone** (Step1.1 QWEN): **fails on 16 GB VRAM** with
  `torch.OutOfMemoryError` during the refinement stage. 27 images
  saved before the crash (faces + an "Original" reference sheet).
  Not a wrapper bug — QWEN's 14 GB GGUF + 9 GB CLIP + SDXL refinement
  exceeds 16 GB. Documented in gotchas as a hardware requirement;
  users on small-VRAM GPUs should skip clone and stick to Step1+Step2.

Wrapper fixes this round: `init_costume_via_rest` helper
(commit `770838d`) + 3 more tests for clothing_add's new flow.
Full suite: 272 passing, 1 skipped.

Commits this round: `770838d` (clothing REST-init), plus
`d3560a3` (clone LoadImage + clothing prune from earlier).

All 6 Wave 2 commands now pass live validation + submission on this
GPU; 5 run to completion end-to-end; 1 (clone) OOMs on 16 GB and
needs ≥24 GB VRAM for the QWEN stack.
