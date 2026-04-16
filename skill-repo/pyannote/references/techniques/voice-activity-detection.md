# Voice Activity Detection

Detect speech regions in an audio file without identifying who is speaking. VAD is a foundational building block — useful standalone for silence removal and audio indexing, and used internally by the diarization pipeline.

## Overview

Voice activity detection answers: "where is there speech?" It returns time segments labeled as `SPEECH`, with no speaker identity. This is faster and lighter than full diarization.

> **Note:** The `pyannote/voice-activity-detection` pipeline is incompatible with pyannote.audio v4.x (uses deprecated `@`-revision syntax). The CLI's `vad` command works around this by running the diarization pipeline and collapsing all speaker labels into "SPEECH" regions. Results are equivalent but processing is heavier than a dedicated VAD model.

## Basic Usage

```python
from pyannote.audio import Pipeline
import os

# Load the VAD pipeline
# NOTE: pyannote/voice-activity-detection is incompatible with pyannote.audio v4.x.
# The CLI vad command uses the diarization pipeline instead (see Note above).
pipeline = Pipeline.from_pretrained(
    "pyannote/voice-activity-detection",
    token=os.environ["HF_TOKEN"]
)

# Run VAD — returns an Annotation object
vad = pipeline("audio.wav")

# Iterate over speech segments
for segment, _, label in vad.itertracks(yield_label=True):
    print(f"{segment.start:.1f}s - {segment.end:.1f}s  [{label}]")
    # label is always "SPEECH"
```

## Working with VAD Output

```python
# Get all speech segments as a list
speech_segments = list(vad.itertracks())

# Check total speech duration
speech_timeline = vad.get_timeline().support()
total_speech = sum(seg.duration for seg in speech_timeline)
print(f"Total speech: {total_speech:.1f}s")

# Get speech fraction
import soundfile as sf
info = sf.info("audio.wav")
total_duration = info.duration
print(f"Speech ratio: {total_speech / total_duration:.1%}")
```

## Extracting Speech Regions

```python
import numpy as np
import soundfile as sf

# Load audio
audio, sr = sf.read("audio.wav")

# Extract only speech segments
speech_chunks = []
for segment, _, _ in vad.itertracks(yield_label=True):
    start_sample = int(segment.start * sr)
    end_sample = int(segment.end * sr)
    speech_chunks.append(audio[start_sample:end_sample])

# Concatenate all speech
speech_only = np.concatenate(speech_chunks)
sf.write("speech_only.wav", speech_only, sr)
```

## Using as a Preprocessing Step

VAD output can feed directly into downstream tasks:

```python
from pyannote.audio import Pipeline
from pyannote.core import Segment

# Step 1: Detect speech
# NOTE: pyannote/voice-activity-detection is incompatible with pyannote.audio v4.x.
vad_pipeline = Pipeline.from_pretrained(
    "pyannote/voice-activity-detection",
    token=os.environ["HF_TOKEN"]
)
vad_output = vad_pipeline("audio.wav")

# Step 2: Use speech timeline for targeted embedding extraction
from pyannote.audio import Model, Inference

model = Model.from_pretrained(
    "pyannote/wespeaker-voxceleb-resnet34-LM",
    token=os.environ["HF_TOKEN"]
)
inference = Inference(model, window="sliding", duration=2.0, step=0.5)

# Only process speech regions
for segment, _, _ in vad_output.itertracks(yield_label=True):
    if segment.duration > 1.0:  # skip very short segments
        embedding = inference.crop("audio.wav", segment)
        print(f"Embedding for {segment}: shape {embedding.shape}")
```

## Export VAD Results

```python
# Write RTTM
with open("vad.rttm", "w") as f:
    vad.write_rttm(f)

# Write as simple tab-separated
for segment, _, label in vad.itertracks(yield_label=True):
    print(f"{segment.start:.3f}\t{segment.end:.3f}\t{label}")
```

## Use Cases

- **Silence removal**: extract only speech for downstream processing
- **Audio indexing**: build a searchable index of when speech occurs
- **Preprocessing for diarization**: reduces data fed to expensive embedding models
- **Transcription windowing**: skip silent regions before sending to ASR
- **Meeting analytics**: compute speaking-time ratios, silence gaps

## Gotchas

- **Music and noise**: VAD may label non-speech sounds as speech. Tune the threshold if needed.
- **Short silence gaps**: very brief pauses within speech may be included in speech segments. Use `.support()` to merge nearby segments.
- **Token required**: same HuggingFace token and model acceptance requirement as diarization.

## Sources

- pyannote.audio GitHub: https://github.com/pyannote/pyannote-audio
- VAD model card: https://huggingface.co/pyannote/voice-activity-detection
- Segmentation model card: https://huggingface.co/pyannote/segmentation-3.0
- pyannote.audio tutorials: https://github.com/pyannote/pyannote-audio/blob/develop/tutorials/
