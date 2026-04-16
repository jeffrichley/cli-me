# Speaker Verification

Determine whether two audio samples contain the same speaker. Speaker verification is a binary decision: "same speaker" or "different speaker", based on cosine similarity between speaker embeddings.

## Overview

Verification workflow:
1. Extract speaker embeddings from each audio sample
2. Compute cosine similarity between the two embeddings
3. Apply a threshold to make the same/different decision

This is distinct from diarization (which segments a single file) and identification (which matches against a known set). Verification requires only two samples and no enrollment database.

## Using the SpeakerVerification Pipeline

```python
from pyannote.audio.pipelines import SpeakerVerification
import os

# Load the verification pipeline
pipeline = SpeakerVerification(
    segmentation="pyannote/segmentation",
    embedding="pyannote/embedding",
    use_auth_token=os.environ["HF_TOKEN"]
)

# Compare two audio files
score, prediction = pipeline(
    {"audio": "speaker_a_sample.wav"},
    {"audio": "speaker_b_sample.wav"}
)

print(f"Similarity score: {score:.3f}")
print(f"Same speaker: {prediction}")  # True or False
```

## Manual Embedding Comparison

For more control, extract embeddings yourself and compare:

```python
from pyannote.audio import Inference
from pyannote.core import Segment
import numpy as np

# Load embedding model
inference = Inference(
    "pyannote/wespeaker-resnet34-voxceleb",
    use_auth_token=os.environ["HF_TOKEN"],
    window="whole"
)

# Extract embeddings from both samples
embedding_a = inference("speaker_a.wav")  # shape: (1, embedding_dim)
embedding_b = inference("speaker_b.wav")

# Compute cosine similarity
from numpy.linalg import norm

def cosine_similarity(a, b):
    a = a.flatten()
    b = b.flatten()
    return np.dot(a, b) / (norm(a) * norm(b))

score = cosine_similarity(embedding_a, embedding_b)
print(f"Cosine similarity: {score:.4f}")

# Apply threshold (tune this for your use case)
THRESHOLD = 0.7
is_same_speaker = score > THRESHOLD
print(f"Same speaker: {is_same_speaker}")
```

## Extracting Embeddings from Specific Segments

When comparing specific speech regions (not whole files):

```python
from pyannote.audio import Inference
from pyannote.core import Segment

inference = Inference(
    "pyannote/wespeaker-resnet34-voxceleb",
    use_auth_token=os.environ["HF_TOKEN"],
    window="whole"
)

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
from pyannote.audio import Inference

inference = Inference(
    "pyannote/wespeaker-resnet34-voxceleb",
    use_auth_token=os.environ["HF_TOKEN"],
    window="whole"
)

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
if best_score > THRESHOLD:
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

## Sources

- pyannote.audio GitHub: https://github.com/pyannote/pyannote-audio
- wespeaker-resnet34 model: https://huggingface.co/pyannote/wespeaker-resnet34-voxceleb
- wespeaker-resnet152 model: https://huggingface.co/pyannote/wespeaker-resnet152-voxceleb
- pyannote embedding model: https://huggingface.co/pyannote/embedding
- VoxCeleb dataset: https://www.robots.ox.ac.uk/~vgg/data/voxceleb/
