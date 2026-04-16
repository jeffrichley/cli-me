# Embedding Extraction

Extract fixed-length vector representations of speaker identity from audio. Embeddings encode "who is speaking" as a point in a high-dimensional space — similar speakers cluster together, different speakers are far apart.

## Overview

Speaker embeddings are the foundation for:
- Speaker verification (compare two embeddings)
- Speaker clustering (group similar embeddings)
- Speaker search (find the closest match in a database)
- Diarization (clustering step uses embeddings internally)

## Basic Extraction

```python
from pyannote.audio import Model, Inference
import os

# Load the embedding model (two-step pattern)
model = Model.from_pretrained(
    "pyannote/wespeaker-resnet34-voxceleb",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model, window="whole")  # treat the entire file as one segment

# Extract embedding from a file
embedding = inference("audio.wav")
print(f"Embedding shape: {embedding.shape}")  # (1, 256)
print(f"Embedding dtype: {embedding.dtype}")  # float32
```

## Available Models

```python
# Lightweight — fast, good for most use cases
model = Model.from_pretrained(
    "pyannote/wespeaker-resnet34-voxceleb",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model)

# High-quality — more accurate, slower, larger
model = Model.from_pretrained(
    "pyannote/wespeaker-resnet152-voxceleb",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model)
```

| Model | Architecture | Embedding dim | Speed | Accuracy |
|-------|-------------|---------------|-------|----------|
| wespeaker-resnet34-voxceleb  | ResNet-34  | 256 | Fast | Good |
| wespeaker-resnet152-voxceleb | ResNet-152 | 256 | Slow | Better |

## Extracting from a Specific Time Range

```python
from pyannote.audio import Model, Inference
from pyannote.core import Segment

model = Model.from_pretrained(
    "pyannote/wespeaker-resnet34-voxceleb",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model, window="whole")

# Crop to a specific segment before extracting
segment = Segment(5.0, 12.0)  # 5s to 12s
embedding = inference.crop("audio.wav", segment)
print(f"Shape: {embedding.shape}")  # (1, 256)
```

## Sliding Window Embeddings

For long files, extract embeddings over a sliding window:

```python
from pyannote.audio import Model, Inference

model = Model.from_pretrained(
    "pyannote/wespeaker-resnet34-voxceleb",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model, window="sliding", duration=3.0, step=1.0)

# Returns SlidingWindowFeature: (num_windows, embedding_dim)
embeddings = inference("audio.wav")
print(f"Shape: {embeddings.data.shape}")

# Access individual window embeddings
for i, (window, embedding) in enumerate(embeddings):
    print(f"Window {i}: {window.start:.1f}s - {window.end:.1f}s, shape {embedding.shape}")
```

## Embeddings from Diarization Output

When you've already run diarization, `DiarizeOutput` includes per-speaker embeddings:

```python
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token=os.environ["HF_TOKEN"]
)

output = pipeline("audio.wav")

# Speaker embeddings: (num_speakers, embedding_dim)
speaker_embeddings = output.speaker_embeddings
print(f"Speakers found: {len(output.speaker_diarization.labels())}")
print(f"Embeddings shape: {speaker_embeddings.shape}")  # e.g. (3, 256)

# Map speaker labels to their embeddings
labels = output.speaker_diarization.labels()
for i, speaker in enumerate(labels):
    emb = speaker_embeddings[i]
    print(f"{speaker}: embedding norm = {float(np.linalg.norm(emb)):.3f}")
```

## Speaker Clustering

Group audio segments by speaker identity without a reference database:

```python
from pyannote.audio import Model, Inference
from pyannote.core import Segment
import numpy as np
from sklearn.cluster import AgglomerativeClustering

model = Model.from_pretrained(
    "pyannote/wespeaker-resnet34-voxceleb",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model, window="whole")

# Segments to cluster (e.g., from VAD output)
segments = [
    Segment(0.5, 3.0),
    Segment(3.5, 6.0),
    Segment(6.5, 9.0),
    Segment(10.0, 13.0),
]

# Extract embeddings for each segment
embeddings = np.vstack([
    inference.crop("audio.wav", seg).flatten()
    for seg in segments
])

# Cluster into 2 speakers
clustering = AgglomerativeClustering(n_clusters=2, metric="cosine", linkage="average")
labels = clustering.fit_predict(embeddings)

for seg, label in zip(segments, labels):
    print(f"{seg.start:.1f}s - {seg.end:.1f}s  SPEAKER_{label:02d}")
```

## Normalizing Embeddings

L2-normalize before cosine similarity for consistent behavior:

```python
import numpy as np

def normalize(embedding):
    """L2-normalize embedding to unit sphere."""
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm

emb_a = normalize(inference("audio_a.wav").flatten())
emb_b = normalize(inference("audio_b.wav").flatten())

# After L2 normalization, cosine similarity = dot product
similarity = float(np.dot(emb_a, emb_b))
```

## GPU Acceleration

```python
import torch

model = Model.from_pretrained(
    "pyannote/wespeaker-resnet34-voxceleb",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model, window="whole")

# Move to GPU
inference.to(torch.device("cuda"))

# Now extraction runs on GPU
embedding = inference("audio.wav")
```

## Gotchas

- **Short segments**: embeddings from < 1s of speech are unreliable. Aim for 2s+ of clean speech.
- **Silence and noise**: passing non-speech audio through the embedding model produces meaningless vectors. Always run VAD first and crop to speech regions.
- **`window="whole"` vs `window="sliding"`**: `"whole"` produces one embedding per call. `"sliding"` produces a time series. Choose based on your task.
- **HF token required**: model acceptance on HuggingFace is required.

## Sources

- pyannote.audio GitHub: https://github.com/pyannote/pyannote-audio
- wespeaker-resnet34-voxceleb: https://huggingface.co/pyannote/wespeaker-resnet34-voxceleb
- wespeaker-resnet152-voxceleb: https://huggingface.co/pyannote/wespeaker-resnet152-voxceleb
- pyannote Inference API: https://github.com/pyannote/pyannote-audio/blob/develop/src/pyannote/audio/core/inference.py
