# Internal Architecture

## Module Structure

```
demucs/
├── __main__.py          # Entry → separate.main()
├── separate.py          # CLI arg parsing + main loop
├── api.py               # High-level Separator class
├── apply.py             # apply_model() — core inference with chunking/shifts
├── pretrained.py        # Model loading from torch.hub / local repo
├── audio.py             # Audio I/O (load via ffmpeg, save WAV/MP3/FLAC)
├── htdemucs.py          # Hybrid Transformer Demucs model (v4)
├── hdemucs.py           # Hybrid Demucs model (v3)
├── demucs.py            # Original waveform Demucs model
├── spec.py              # Spectrogram utilities
├── states.py            # Model state management
├── transformer.py       # Cross-attention transformer layers
├── filtering.py         # Wiener filtering
├── utils.py             # Misc utilities
└── remote/              # YAML configs for pretrained model bags
    ├── htdemucs.yaml
    ├── htdemucs_ft.yaml
    ├── htdemucs_6s.yaml
    ├── mdx.yaml
    ├── mdx_extra.yaml
    └── ...
```

## Model Hierarchy

1. **Demucs** (demucs.py) — Original waveform-domain U-Net
2. **HDemucs** (hdemucs.py) — Hybrid: spectrogram + waveform branches
3. **HTDemucs** (htdemucs.py) — Hybrid Transformer: adds cross-attention
4. **BagOfModels** (apply.py) — Ensemble: weighted average of multiple models

## Inference Pipeline (`apply.py`)

1. Model moved to device
2. If shifts > 0: apply random time shifts, run model, average results
3. If split enabled: chunk audio into segments with overlap
4. For each chunk: run model forward pass
5. Blend overlapping chunks with linear crossfade
6. If BagOfModels: weighted average across sub-models
7. Results returned on original device

## Device Flow

- Default: `"cuda" if torch.cuda.is_available() else "cpu"`
- Multi-worker threading only when `device.type == "cpu"` and `jobs > 0`
- For BagOfModels: each sub-model restored to original device after compute

## Sources (stems)

Default 4 sources: `["drums", "bass", "other", "vocals"]`
6-source model adds: piano, guitar (experimental)
