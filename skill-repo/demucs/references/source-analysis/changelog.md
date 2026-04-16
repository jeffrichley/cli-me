# Demucs Changelog (Notable Versions)

## v4.0 (Hybrid Transformer Demucs)
- Introduced HTDemucs architecture with cross-attention transformer
- New default model: `htdemucs`
- Added fine-tuned variant: `htdemucs_ft`
- Added 6-stem model: `htdemucs_6s` (drums, bass, other, vocals, piano, guitar)
- Python API via `demucs.api.Separator`
- FLAC output support

## v3.0 (Hybrid Demucs)
- Hybrid spectrogram + waveform architecture
- MDX challenge models: `mdx`, `mdx_extra`, `mdx_q`, `mdx_extra_q`
- Quantized model variants for smaller downloads

## v2.0
- Improved waveform-domain model
- Equivariant stabilization (shifts)

## v1.0
- Original waveform-domain U-Net architecture
