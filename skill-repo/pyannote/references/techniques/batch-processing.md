# Batch Processing

Process multiple audio files efficiently. The key principle: load the pipeline once and apply it to many files. Pipeline initialization is expensive (~5–15 seconds); inference per file is the bottleneck you want to parallelize.

## Basic Pattern: Load Once, Apply Many

```python
from pyannote.audio import Pipeline
import os
from pathlib import Path

# Load pipeline ONCE outside the loop
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    use_auth_token=os.environ["HF_TOKEN"]
)

input_dir = Path("/path/to/audio/files")
output_dir = Path("/path/to/output")
output_dir.mkdir(parents=True, exist_ok=True)

audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3"))

for audio_path in audio_files:
    print(f"Processing: {audio_path.name}")
    output = pipeline(str(audio_path))

    # Write RTTM alongside input file
    rttm_path = output_dir / audio_path.with_suffix(".rttm").name
    with open(rttm_path, "w") as f:
        output.speaker_diarization.write_rttm(f)

    print(f"  -> {rttm_path}")
```

## Preserving Directory Structure

When your input has subdirectories, mirror the structure in the output:

```python
from pathlib import Path
import os
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    use_auth_token=os.environ["HF_TOKEN"]
)

input_root = Path("/data/audio")
output_root = Path("/data/rttm")

for audio_path in input_root.rglob("*.wav"):
    # Build matching output path
    relative = audio_path.relative_to(input_root)
    rttm_path = output_root / relative.with_suffix(".rttm")
    rttm_path.parent.mkdir(parents=True, exist_ok=True)

    if rttm_path.exists():
        print(f"Skip (already done): {relative}")
        continue

    print(f"Processing: {relative}")
    output = pipeline(str(audio_path))

    with open(rttm_path, "w") as f:
        output.speaker_diarization.write_rttm(f)
```

## Progress Hooks

Track pipeline progress per file:

```python
from pyannote.audio.pipelines.utils.hook import ProgressHook

for audio_path in audio_files:
    print(f"\nProcessing: {audio_path.name}")
    with ProgressHook() as hook:
        output = pipeline(str(audio_path), hook=hook)
    # ProgressHook prints step names and completion status
```

Custom progress callback:

```python
def make_hook(filename):
    def hook(step_name, step_artifact, file=None, total=None, completed=None):
        if completed is not None and total is not None:
            pct = int(100 * completed / total)
            print(f"  [{filename}] {step_name}: {pct}%", end="\r")
    return hook

for audio_path in audio_files:
    output = pipeline(str(audio_path), hook=make_hook(audio_path.name))
    print()  # newline after progress
```

## Multiprocessing (True Parallelism)

The pipeline is **not thread-safe**, but works fine with `multiprocessing`:

```python
import os
import multiprocessing as mp
from pathlib import Path
from pyannote.audio import Pipeline

def process_file(args):
    """Each worker process loads its own pipeline instance."""
    audio_path, output_dir, hf_token = args

    # Each worker must load its own pipeline
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-community-1",
        use_auth_token=hf_token
    )

    output_path = Path(output_dir) / Path(audio_path).with_suffix(".rttm").name
    output = pipeline(audio_path)

    with open(output_path, "w") as f:
        output.speaker_diarization.write_rttm(f)

    return audio_path, str(output_path)

if __name__ == "__main__":
    audio_files = [str(p) for p in Path("/data/audio").glob("*.wav")]
    output_dir = "/data/rttm"
    hf_token = os.environ["HF_TOKEN"]

    args = [(f, output_dir, hf_token) for f in audio_files]

    # Use 2–4 workers (GPU VRAM is the bottleneck, not CPU cores)
    with mp.Pool(processes=2) as pool:
        for audio, rttm in pool.imap_unordered(process_file, args):
            print(f"Done: {Path(audio).name} -> {rttm}")
```

Note: On GPU, multiple workers share VRAM. With `num_workers=2` and ~2GB per pipeline, you need ~4GB VRAM. Scale accordingly.

## Resumable Batch Jobs

Skip files that already have output (safe to re-run):

```python
from pathlib import Path
from pyannote.audio import Pipeline
import os

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    use_auth_token=os.environ["HF_TOKEN"]
)

input_dir = Path("/data/audio")
output_dir = Path("/data/rttm")
output_dir.mkdir(exist_ok=True)

audio_files = sorted(input_dir.glob("*.wav"))
pending = [
    f for f in audio_files
    if not (output_dir / f.with_suffix(".rttm").name).exists()
]

print(f"Total: {len(audio_files)}, Pending: {len(pending)}, Done: {len(audio_files) - len(pending)}")

for i, audio_path in enumerate(pending, 1):
    print(f"[{i}/{len(pending)}] {audio_path.name}")
    output = pipeline(str(audio_path))
    rttm_path = output_dir / audio_path.with_suffix(".rttm").name
    with open(rttm_path, "w") as f:
        output.speaker_diarization.write_rttm(f)
```

## Large File Handling

pyannote processes audio in overlapping windows internally — it does not load the entire file into memory at once. Memory usage scales with batch size, not file duration.

```python
# For very long files, reduce batch sizes to control peak memory
pipeline.segmentation_batch_size = 8
pipeline.embedding_batch_size = 8

# Process a 2-hour file — memory stays bounded
output = pipeline("two_hour_interview.wav")
```

## Error Handling in Batch Jobs

Don't let one bad file kill the whole batch:

```python
import traceback
from pathlib import Path

errors = []

for audio_path in audio_files:
    try:
        output = pipeline(str(audio_path))
        rttm_path = output_dir / audio_path.with_suffix(".rttm").name
        with open(rttm_path, "w") as f:
            output.speaker_diarization.write_rttm(f)
        print(f"OK: {audio_path.name}")
    except Exception as e:
        print(f"FAILED: {audio_path.name} — {e}")
        errors.append((audio_path, traceback.format_exc()))

if errors:
    print(f"\n{len(errors)} files failed:")
    for path, tb in errors:
        print(f"  {path.name}")
        print(tb)
```

## Gotchas

- **One pipeline instance per process**: do not share a pipeline across threads. Use `multiprocessing`, not `threading`.
- **GPU memory accumulates**: if running many files sequentially on GPU and memory grows, call `torch.cuda.empty_cache()` between files.
- **First file is slowest**: the first inference call JIT-compiles CUDA kernels. Subsequent calls are faster.
- **MP3 and AAC support**: requires `ffmpeg` on PATH. WAV files work out of the box.

```python
import torch

for audio_path in audio_files:
    output = pipeline(str(audio_path))
    # ... save output ...
    torch.cuda.empty_cache()  # release intermediate tensors
```

## Sources

- pyannote.audio GitHub: https://github.com/pyannote/pyannote-audio
- pyannote model hub: https://huggingface.co/pyannote
- ProgressHook source: https://github.com/pyannote/pyannote-audio/blob/develop/pyannote/audio/pipelines/utils/hook.py
- PyTorch multiprocessing: https://pytorch.org/docs/stable/multiprocessing.html
