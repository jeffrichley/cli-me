# pyannote Skill Build Log

Append-only. Newest entries at the bottom.

---

**2026-04-16** — Initial research completed. Analyzed pyannote.audio 4.0.4
(commit 78c0d16). Created 5 source analysis pages and 7 technique pages.
Installed version matches source exactly — no unreleased features to worry about.
Key insight: the Python API is much richer than the CLI, so the wrapper should
use `Pipeline.from_pretrained()` + `pipeline()` directly rather than shelling
out to pyannote-audio.exe.
