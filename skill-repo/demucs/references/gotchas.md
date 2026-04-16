# Gotchas

## CUDA / GPU

- **CUDA out of memory**: Default segment size may exceed GPU VRAM on cards
  with <4 GB. Use `--segment 7` or lower. Or fall back to `--device cpu`.
- **GPU not detected**: PyTorch must be installed with CUDA support. Check with
  `python -c "import torch; print(torch.cuda.is_available())"`. If False,
  reinstall PyTorch from https://pytorch.org/get-started/locally/
- **Multi-GPU**: Demucs uses a single GPU. `CUDA_VISIBLE_DEVICES` selects which
  one, but it won't split work across GPUs.
- **`--jobs` ignored on GPU**: The parallel workers flag only applies to CPU
  processing. On GPU, the GPU handles parallelism internally.

## Audio

- **ffmpeg required**: Demucs loads audio via ffmpeg subprocess. If ffmpeg is
  not installed, audio loading fails. Install with `pip install ffmpeg-python`
  or system package manager.
- **MP3 output requires lameenc**: The `--mp3` flag uses the `lameenc` Python
  package. Install with `pip install lameenc` if missing.
- **Sample rate**: All current models operate at 44100 Hz. Input is
  auto-resampled; output is always 44100 Hz regardless of input rate.

## Audio Output

- **WAV/FLAC save fails on Windows (`Could not load libtorchcodec`)**: Two
  prerequisites must be met:
  1. **torchcodec must match PyTorch**: Check the compatibility table at
     https://github.com/pytorch/torchcodec (e.g., PyTorch 2.11 needs
     torchcodec 0.11).
  2. **ffmpeg shared DLLs must be next to ffmpeg.exe**: torchcodec finds
     ffmpeg via `shutil.which("ffmpeg")` and loads DLLs from that directory.
     The common "essentials" build is statically linked and lacks these DLLs.
     Download the "full-shared" build from
     https://github.com/BtbN/FFmpeg-Builds/releases and copy the DLLs
     (`avcodec-*.dll`, `avformat-*.dll`, etc.) into the directory where
     `ffmpeg.exe` lives.
  - MP3 output always works (uses lameenc, not torchaudio) as a fallback.

## Windows-Specific

- **`mkl_intel_thread.dll` not found**: Fix with
  `conda install -c defaults intel-openmp -f`
- **Permission errors**: Run Anaconda Prompt as Administrator
- **32-bit Python not supported**: Demucs requires 64-bit Python

## Models

- **First run downloads models**: Initial invocation downloads ~80-300 MB of
  model weights from torch.hub. This can be slow or fail behind proxies.
- **6-stem model (`htdemucs_6s`)**: Piano separation is experimental and
  lower quality than the 4-stem separations.
- **`--segment` limit for HTDemucs**: The maximum segment for htdemucs is 7.8
  seconds (its trained segment length). Setting `--segment 8` or higher will
  cause a FATAL error: "Cannot use a Transformer model with a longer segment
  than it was trained for." Omit `--segment` to use the model's default, or
  set it to 7 or lower for reduced VRAM usage.

## Unsupported Upstream Flags

- **`--filename` (output template)**: Demucs supports `--filename "{track}/{stem}.{ext}"`
  for custom output paths, but the CLI wrapper does not expose this. Output always uses
  demucs's default: `{output}/{model}/{track}/{stem}.{ext}`.
- **`--other-method`**: Exists in unreleased source but not in PyPI 4.0.1.
- **`--sig`**: For locally trained model signatures. Not wrapped.
- **`--clip-mode none`**: Exists in unreleased source but demucs 4.0.1 only accepts
  `rescale` and `clamp`.

## Processing

- **Long files + `--no-split`**: Processing a full song without splitting
  requires enough memory to hold the entire waveform. For a 5-minute song
  at 44100 Hz stereo, that's ~100 MB of raw audio tensors per stem.
- **`--shifts 0`**: Setting shifts to 0 disables the stabilization entirely.
  Use `--shifts 1` (default) for the baseline behavior.
