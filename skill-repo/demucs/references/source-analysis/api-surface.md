# API Surface

## Entry Points

### CLI Entry Point
- Console script: `demucs` → `demucs.separate:main()`
- Module invocation: `python -m demucs` → `demucs/__main__.py` → `separate.main()`

### Python API (`demucs.api`)
- `Separator` class — main high-level interface
- `list_models()` — enumerate available pretrained models
- `save_audio()` — write tensor to WAV/MP3/FLAC

### Lower-Level API
- `demucs.pretrained.get_model(name)` — load a model by name
- `demucs.apply.apply_model(model, mix, ...)` — run separation on a tensor
- `demucs.audio.save_audio(wav, path, ...)` — save audio with format options

### torch.hub
- `torch.hub.load('facebookresearch/demucs', 'get_model', model='htdemucs')`

## Separator Class (`demucs/api.py`)

```python
Separator(
    model: str = "htdemucs",
    repo: Optional[Path] = None,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    shifts: int = 1,
    overlap: float = 0.25,
    split: bool = True,
    segment: Optional[int] = None,
    jobs: int = 0,
    progress: bool = False,
    callback: Optional[Callable] = None,
    callback_arg: Optional[dict] = None,
)
```

### Methods
- `separate_audio_file(file: Path)` → `(origin_tensor, {stem_name: tensor})`
- `separate_tensor(wav: Tensor, sr: Optional[int])` → `(origin_tensor, {stem_name: tensor})`
- `update_parameter(...)` — modify params after init

### Properties
- `samplerate` — model's native sample rate (typically 44100)
- `audio_channels` — expected channel count
- `model` — the loaded `nn.Module`

## Audio I/O (`demucs/audio.py`)

### save_audio()
```python
save_audio(
    wav: Tensor,
    path: Union[str, Path],
    samplerate: int,
    bitrate: int = 320,
    clip: str = "rescale",      # rescale | clamp | tanh | none
    bits_per_sample: int = 16,  # 16 | 24 | 32
    as_float: bool = False,
    preset: int = 2             # MP3 encoder preset 2-7
)
```

### load_track()
- Loads via ffmpeg subprocess (primary) or torchaudio (fallback)
- Supports any format ffmpeg can decode
- Auto-resamples to model's native rate
