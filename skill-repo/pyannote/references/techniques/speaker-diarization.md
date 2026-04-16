# Speaker Diarization

"Who spoke when" — the primary use case for pyannote.audio. Speaker diarization segments an audio file by speaker identity, producing timestamped speaker turns without requiring pre-enrollment.

## Overview

The `pyannote/speaker-diarization-community-1` pipeline runs end-to-end diarization:
1. Voice activity detection (find speech regions)
2. Speaker segmentation (find speaker changes)
3. Speaker embedding extraction (represent each speaker)
4. Clustering (group segments by identity)

## Basic Usage

```python
from pyannote.audio import Pipeline
import torch

# Load the pipeline (downloads ~500MB on first run)
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    use_auth_token="hf_your_token_here"
)

# Or use the HF_TOKEN environment variable (recommended)
import os
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    use_auth_token=os.environ["HF_TOKEN"]
)

# Run diarization
output = pipeline("audio.wav")

# Iterate over speaker turns
for segment, track, speaker in output.speaker_diarization.itertracks(yield_label=True):
    print(f"{segment.start:.1f}s - {segment.end:.1f}s  [{speaker}]")
```

## Controlling Speaker Count

When you know or can estimate the number of speakers:

```python
# Exact speaker count (best accuracy when you know it)
output = pipeline("audio.wav", num_speakers=3)

# Constrained range (useful when count is roughly known)
output = pipeline("audio.wav", min_speakers=2, max_speakers=5)
```

## Output Object

`pipeline()` returns a `DiarizeOutput` with these fields:

```python
output = pipeline("audio.wav")

# Primary result: Annotation with speaker labels
annotation = output.speaker_diarization

# Exclusive (no overlapping speech) version
exclusive = output.exclusive_speaker_diarization

# Speaker embedding matrix: (num_speakers, embedding_dim)
embeddings = output.speaker_embeddings
print(f"Found {len(annotation.labels())} speakers")
print(f"Embedding shape: {embeddings.shape}")
```

## Exporting Results

### RTTM Format

```python
# Write RTTM file
with open("output.rttm", "w") as f:
    output.speaker_diarization.write_rttm(f)

# RTTM lines look like:
# SPEAKER audio 1 0.500 1.200 <NA> <NA> SPEAKER_00 <NA> <NA>
```

### JSON via serialize()

```python
import json

data = output.serialize()
# data is a dict with diarization entries
print(json.dumps(data, indent=2))

# Structure:
# {
#   "diarization": [
#     {"start": 0.5, "end": 1.7, "speaker": "SPEAKER_00"},
#     ...
#   ]
# }
```

### Direct Annotation Iteration

```python
for segment, _, speaker in output.speaker_diarization.itertracks(yield_label=True):
    start = segment.start
    end = segment.end
    duration = end - start
    print(f"{speaker}: {start:.3f} --> {end:.3f} ({duration:.1f}s)")
```

## GPU Acceleration

```python
# Move pipeline to GPU before running
pipeline.to(torch.device("cuda"))
output = pipeline("audio.wav")

# Apple Silicon (MPS)
pipeline.to(torch.device("mps"))

# Check available device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
pipeline.to(device)
```

## Performance Tuning

```python
# Increase batch sizes for faster processing on GPU
pipeline.segmentation_batch_size = 32
pipeline.embedding_batch_size = 32

# Reduce for low-VRAM situations
pipeline.segmentation_batch_size = 4
pipeline.embedding_batch_size = 4
```

## Progress Tracking

```python
from pyannote.audio.pipelines.utils.hook import ProgressHook

with ProgressHook() as hook:
    output = pipeline("audio.wav", hook=hook)
```

## Gotchas

- **First run downloads ~500MB** of model weights to `~/.cache/huggingface/`. Subsequent runs use the cache and are fast.
- **HuggingFace token required**: You must visit the model page, accept the terms, and use a token that has been granted access. A token without model acceptance will get a 401 error.
- **Audio format**: WAV files work reliably. For MP3/other formats, pyannote uses `soundfile` and `librosa` — ensure they are installed.
- **Overlapping speech**: The default output includes overlapping segments. Use `exclusive_speaker_diarization` if you need non-overlapping turns.
- **Short segments**: Very short segments (< 0.5s) may be unreliable. Filter by duration if needed.

## Sources

- pyannote.audio GitHub: https://github.com/pyannote/pyannote-audio
- Model card (speaker diarization): https://huggingface.co/pyannote/speaker-diarization-community-1
- pyannote.audio documentation: https://github.com/pyannote/pyannote-audio/blob/develop/tutorials/
- RTTM format spec: https://catalog.ldc.upenn.edu/docs/LDC2004T12/RTTM-format-v13.pdf
