# Log

## 2026-04-15: Initial research completed

Analyzed Demucs v4.0.1 (Hybrid Transformer Demucs) from
https://github.com/facebookresearch/demucs (shallow clone).

Created source analysis pages:
- API surface: Separator class, apply_model, save_audio, torch.hub
- CLI interface: Complete flag reference for `demucs` command
- Internal architecture: Module structure, model hierarchy, inference pipeline
- Key functions: main(), Separator, apply_model, save_audio

Created technique pages:
- separate-stems: Full 4-stem separation
- extract-vocals: Two-stem mode for vocal isolation
- output-formats: WAV/MP3/FLAC with bit depth options
- gpu-optimization: CUDA auto-detection, VRAM management, shifts
- model-selection: Comparison of all pretrained models
- batch-processing: Multi-file workflows

Key findings:
- Device auto-detection via `torch.cuda.is_available()` — works out of the box
- No interactive prompts — safe for agent use without suppression flags
- Models download on first use via torch.hub cache
- ffmpeg required as runtime dependency for audio loading

## 2026-04-15: Scaffold and implementation completed

CLI package at `scripts/demucs_cli/` with Typer commands:
- `separate` — split audio into stems with all Demucs flags
- `list-models` — enumerate available pretrained models

Key implementation decisions:
- Device auto-detection reports which device was chosen (cuda/cpu)
- `--format` validates known values (mp3, flac, wav) and rejects unknowns
- `list-models` uses Python API to enumerate YAML configs (not `--list-models`
  which doesn't exist in demucs 4.0.1 from PyPI)
- `--other-method` removed — unreleased feature not in PyPI 4.0.1

Discovered during integration testing:
- htdemucs max segment is 7.8 seconds, not 8 (FATAL error if exceeded)
- torchaudio >= 2.11 on Windows with "essentials" ffmpeg breaks WAV/FLAC save
  (torchcodec needs shared DLLs). MP3 output (via lameenc) always works.
- demucs.api module doesn't exist in 4.0.1 (only in unreleased source)

Test results: 38 passed, 2 xfailed (torchaudio DLL issue)
- Tier 1: 35 command-graph tests (pure unit, no binary)
- Tier 2: 5 integration tests (real demucs binary + synthetic audio)
- URL check: 13/13 live
- Link check: 0 broken, 0 orphans

R1-R4 adversarial reviews completed. All objective findings fixed.
