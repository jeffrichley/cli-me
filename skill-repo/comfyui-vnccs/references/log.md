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
