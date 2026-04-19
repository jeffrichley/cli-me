# Speaker Verification

Determine whether two audio samples contain the same speaker. Speaker verification is a binary decision: "same speaker" or "different speaker", based on cosine similarity between speaker embeddings.

## Overview

Verification workflow:
1. Load an embedding model via `Model.from_pretrained()`
2. Create an `Inference` wrapper
3. Extract speaker embeddings from each audio sample
4. Compute cosine similarity between the two embeddings
5. Apply a threshold to make the same/different decision

This is distinct from diarization (which segments a single file) and identification (which matches against a known set). Verification requires only two samples and no enrollment database.

> **Note**: pyannote.audio v4.x does not include a `SpeakerVerification` pipeline class. The correct approach is manual embedding comparison using `Model.from_pretrained()` and `Inference`, as shown below.

## Basic Verification

```python
from pyannote.audio import Model, Inference
from numpy.linalg import norm
import numpy as np
import os

# Load the embedding model (two-step pattern)
model = Model.from_pretrained(
    "pyannote/wespeaker-voxceleb-resnet34-LM",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model, window="whole")

# Extract embeddings from both samples
embedding_a = inference("speaker_a.wav")  # shape: (embedding_dim,)
embedding_b = inference("speaker_b.wav")

# Compute cosine similarity
def cosine_similarity(a, b):
    a = a.flatten()
    b = b.flatten()
    return float(np.dot(a, b) / (norm(a) * norm(b)))

score = cosine_similarity(embedding_a, embedding_b)
print(f"Cosine similarity: {score:.4f}")

# Apply threshold (tune this for your use case)
THRESHOLD = 0.7
is_same_speaker = score >= THRESHOLD
print(f"Same speaker: {is_same_speaker}")
```

## Extracting Embeddings from Specific Segments

When comparing specific speech regions (not whole files):

```python
from pyannote.audio import Model, Inference
from pyannote.core import Segment
import os

model = Model.from_pretrained(
    "pyannote/wespeaker-voxceleb-resnet34-LM",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model, window="whole")

# Crop to a specific time range before extracting
segment_a = Segment(1.5, 5.0)  # 1.5s to 5.0s
segment_b = Segment(12.0, 16.0)

embedding_a = inference.crop("long_audio.wav", segment_a)
embedding_b = inference.crop("long_audio.wav", segment_b)

# Now compare as above
```

## Speaker Search (1-to-N Verification)

Compare a query speaker against multiple known speakers:

```python
import numpy as np
from pyannote.audio import Model, Inference
import os

model = Model.from_pretrained(
    "pyannote/wespeaker-voxceleb-resnet34-LM",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model, window="whole")

def cosine_similarity(a, b):
    a, b = a.flatten(), b.flatten()
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# Build a speaker database
known_speakers = {
    "alice": inference("alice_sample.wav"),
    "bob":   inference("bob_sample.wav"),
    "carol": inference("carol_sample.wav"),
}

# Query: who is this?
query_embedding = inference("unknown_speaker.wav")

scores = {
    name: cosine_similarity(query_embedding, emb)
    for name, emb in known_speakers.items()
}

best_match = max(scores, key=scores.get)
best_score = scores[best_match]

print(f"Best match: {best_match} (score={best_score:.3f})")

THRESHOLD = 0.65
if best_score >= THRESHOLD:
    print(f"Identified as: {best_match}")
else:
    print("Unknown speaker (below threshold)")
```

## Threshold Tuning

Cosine similarity ranges from -1 to 1. Typical values:

| Similarity | Interpretation |
|-----------|----------------|
| > 0.85    | Very likely same speaker |
| 0.65–0.85 | Probably same speaker |
| 0.45–0.65 | Uncertain |
| < 0.45    | Likely different speakers |

These are rough guidelines. The right threshold depends on:
- Audio quality and recording conditions
- Speaker gender and age variability in your dataset
- Your tolerance for false accepts vs. false rejects

Use a held-out validation set from your target domain to tune the threshold.

## Use Cases

- **Access control**: verify speaker identity before granting access
- **Podcast speaker tracking**: confirm which host is speaking
- **Call center analytics**: link calls to the same customer across sessions
- **Content deduplication**: group recordings of the same speaker

## Gotchas

- **Clean audio matters**: background noise, music, and channel effects hurt accuracy. Preprocess with VAD first.
- **Minimum duration**: embeddings from very short segments (< 1s) are less reliable. Aim for 3–5s of clean speech.
- **Domain mismatch**: models trained on VoxCeleb may underperform on telephone or noisy speech. Consider fine-tuning.
- **HF token required**: same token and model acceptance requirement as diarization.
- **`verify` vs `embed` normalization**: the `verify` command L2-normalizes embeddings internally before scoring; the `embed` command returns raw embeddings. Cosine comparisons of two `embed` outputs match `verify`'s score (cosine is scale-invariant), but Euclidean / dot-product comparisons need manual normalization. See [embedding-extraction#normalizing-embeddings](embedding-extraction.md#normalizing-embeddings).

## Sources

- pyannote.audio GitHub: https://github.com/pyannote/pyannote-audio
- wespeaker-voxceleb-resnet34-LM model: https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM
- pyannote embedding model: https://huggingface.co/pyannote/embedding
- VoxCeleb dataset: https://www.robots.ox.ac.uk/~vgg/data/voxceleb/
