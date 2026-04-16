# Key Functions

## demucs/separate.py

### `main()` (line 102)
CLI entry point. Parses args, creates Separator, iterates tracks, saves stems.
- Validates segment size for HTDemucs
- Validates stem names
- Builds save_audio kwargs from CLI flags

## demucs/api.py

### `Separator.__init__()` (line 54)
Creates separator with model, device, and processing parameters.
Auto-detects CUDA: `device = "cuda" if th.cuda.is_available() else "cpu"`

### `Separator.separate_audio_file(file)` (line 293)
Loads audio file via `audio.convert_audio()`, delegates to `separate_tensor()`.

### `Separator.separate_tensor(wav, sr)` (line 241)
Core separation: normalizes, calls `apply.apply_model()`, denormalizes, returns dict.

### `list_models(repo)` (line 322)
Returns `{"single": [...], "bag": [...]}` of available model names.

## demucs/apply.py

### `apply_model(model, mix, ...)` (line 155)
The engine. Handles chunking, shifts, BagOfModels dispatch.
- `shifts` random time offsets averaged for stability
- `segment` controls chunk size
- `overlap` controls crossfade region
- Threading pool for CPU parallelism

### `tensor_chunk()` (line 21)
Helper for lazy tensor slicing with padding.

## demucs/audio.py

### `save_audio(wav, path, samplerate, ...)` (line 236)
Saves tensor as WAV (int16/int24/float32), MP3 (via lameenc), or FLAC (via torchaudio).
Applies clipping strategy before save.

### `convert_audio(wav, from_rate, to_rate, channels)` (line 60)
Resamples and converts channel count using julius.

## demucs/pretrained.py

### `get_model(name, repo)` (line ~40)
Loads model by name from torch.hub cache or local repo path.
Returns nn.Module (or BagOfModels for ensemble configs).
