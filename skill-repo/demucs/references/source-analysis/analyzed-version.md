# Analyzed Version

- **Software**: Demucs (Music Source Separation)
- **Repository**: https://github.com/facebookresearch/demucs
- **Commit**: shallow clone (--depth 1) of main branch
- **Date analyzed**: 2026-04-15
- **Version**: v4.0.1 (Hybrid Transformer Demucs)
- **Maintainer note**: Original Meta repo is no longer actively maintained;
  community fork at https://github.com/adefossez/demucs is more current.

## Installation

```bash
pip install demucs
# Or with CUDA:
pip install demucs torch torchaudio --extra-index-url https://download.pytorch.org/whl/cu118
```

Requires: Python 3.8+, ffmpeg (for audio loading), PyTorch, torchaudio
