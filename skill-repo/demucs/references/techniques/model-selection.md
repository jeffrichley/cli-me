# Model Selection

## When to Use

You need to choose the best Demucs model for your use case — balancing
quality, speed, model size, and stem count.

## Technique

Demucs ships with several pretrained models. The default `htdemucs` (Hybrid
Transformer) is the best general-purpose choice. `htdemucs_ft` is a fine-tuned
variant with better quality but 4x slower. MDX models were trained for the
Music Demixing Challenge with different data strategies.

## CLI Commands

### List available models
```bash
uv run demucs_cli.py list-models
```

### Use default model
```bash
uv run demucs_cli.py separate song.mp3
# Uses htdemucs
```

### Use fine-tuned model (best quality)
```bash
uv run demucs_cli.py separate song.mp3 --model htdemucs_ft
```

### Use 6-stem model (experimental piano/guitar)
```bash
uv run demucs_cli.py separate song.mp3 --model htdemucs_6s
```

### Use quantized model (smaller download)
```bash
uv run demucs_cli.py separate song.mp3 --model mdx_extra_q
```

### Use custom model from local folder
```bash
uv run demucs_cli.py separate song.mp3 --model my_model --repo ./models/
```

## Model Comparison

| Model | Stems | SDR (dB) | Speed | Size | Best For |
|-------|-------|----------|-------|------|----------|
| `htdemucs` | 4 | 9.0 | Fast | Normal | General purpose (default) |
| `htdemucs_ft` | 4 | ~9.2 | 4x slower | Normal | Maximum quality |
| `htdemucs_6s` | 6 | — | Fast | Normal | Piano/guitar separation |
| `hdemucs_mmi` | 4 | — | Fast | Normal | Legacy v3 model |
| `mdx` | 4 | 7.3 | Fast | Normal | MDX challenge winner |
| `mdx_extra` | 4 | 8.1 | Fast | Normal | Broader music coverage |
| `mdx_q` | 4 | ~7.3 | Fast | 50% smaller | Storage-constrained |
| `mdx_extra_q` | 4 | ~8.1 | Fast | 50% smaller | Best size/quality ratio |

## Under the Hood

- Models are downloaded from torch.hub on first use and cached locally
- "Bag" models are ensembles of multiple sub-models with weighted averaging
- The `--repo` flag loads models from a local directory instead of downloading
- 6-stem model separates: drums, bass, other, vocals, piano, guitar
  (piano source is still experimental/WIP)
- Quantized models (`_q` suffix) use ~50% less disk space with minimal quality loss.
  **Requires `pip install diffq`** — without it, demucs will error:
  "FATAL: Trying to use DiffQ, but diffq is not installed."
  Note: `diffq` is archived by Meta and may fail to build on Python 3.12+.

## Sources

- https://github.com/facebookresearch/demucs/blob/main/README.md
- https://github.com/facebookresearch/demucs/blob/main/docs/mdx.md
- `demucs/remote/` — YAML configs for each model bag
- `demucs/pretrained.py` — model loading logic

## Learned from Usage

(No entries yet — agents update this section after using the commands.)
