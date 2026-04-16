# Key Functions

Functions the CLI wrapper will call when wrapping pyannote.audio 4.0.4. All verified against source at commit 78c0d16.

## Pipeline loading

### `Pipeline.from_pretrained(checkpoint, token=None, cache_dir=None, revision=None)`

The single entry point for loading any pipeline. Accepts a HuggingFace model ID or a local YAML path.

Returns the pipeline instance, or `None` on failure — the caller must check for `None`.

```python
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token="hf_...",
    cache_dir="/path/to/cache",
)
if pipeline is None:
    raise RuntimeError("Failed to load pipeline")
```

Source: `src/pyannote/audio/core/pipeline.py`

## Running diarization

### `pipeline.__call__(file, num_speakers=None, min_speakers=None, max_speakers=None, return_embeddings=False)`

Run the `SpeakerDiarization` pipeline on an audio file. The `file` argument accepts a path string, a `pathlib.Path`, or a pyannote.database-style dict with an `"audio"` key.

Parameters specific to `SpeakerDiarization`:
- `num_speakers` — fix the number of speakers exactly
- `min_speakers` / `max_speakers` — constrain the speaker count range
- `return_embeddings` — include per-speaker embeddings in the output

Returns a `DiarizeOutput` dataclass (or a plain `Annotation` for VAD-only pipelines).

```python
output = pipeline("audio.wav", num_speakers=2)
output = pipeline("audio.wav", min_speakers=1, max_speakers=5, return_embeddings=True)
```

Source: `src/pyannote/audio/pipelines/speaker_diarization.py`

## Writing output

### `Annotation.write_rttm(file)`

Write the annotation to a file object in RTTM format. Pass `sys.stdout` for stdout output or an open file handle for file output.

```python
with open("output.rttm", "w") as f:
    annotation.write_rttm(f)

# or to stdout
import sys
annotation.write_rttm(sys.stdout)
```

Source: `pyannote.core` (external dependency, not in this repo)

### `DiarizeOutput.serialize() -> dict`

Returns a JSON-serializable dict. Structure:

```json
{
  "diarization": [
    {"start": 0.5, "end": 2.3, "speaker": "SPEAKER_00"},
    ...
  ],
  "exclusive_diarization": [
    {"start": 0.5, "end": 2.3, "speaker": "SPEAKER_00"},
    ...
  ]
}
```

Speaker embeddings are included when `return_embeddings=True` was passed to the pipeline.

Source: `src/pyannote/audio/pipelines/speaker_diarization.py` — `DiarizeOutput.serialize()`

## Iterating results

### `Annotation.itertracks(yield_label=True)`

Iterate over all speech turns. With `yield_label=True`, yields `(segment, track, label)` tuples where:
- `segment` is a `pyannote.core.Segment` with `.start` and `.end` (in seconds)
- `track` is a string track name (usually `"A"` for single-track diarization)
- `label` is the speaker label string (e.g. `"SPEAKER_00"`)

```python
for segment, track, speaker in annotation.itertracks(yield_label=True):
    print(f"{segment.start:.3f} -> {segment.end:.3f}: {speaker}")
```

Source: `pyannote.core` (external dependency)

### `Annotation.labels()`

Return a sorted list of unique speaker labels in the annotation.

```python
speakers = annotation.labels()  # e.g. ["SPEAKER_00", "SPEAKER_01"]
num_speakers = len(annotation.labels())
```

Source: `pyannote.core` (external dependency)

### `Annotation.support()`

Merge overlapping speech segments (across all speakers) and return a `Timeline` of non-overlapping speech regions. Useful for computing total speech duration or building a voice activity detection mask.

```python
speech_timeline = annotation.support()
```

Source: `pyannote.core` (external dependency)

## Audio segment extraction

### `Audio.crop(file, segment)`

Extract a time segment from an audio file without loading the entire file. Returns `(waveform, sample_rate)` where `waveform` is a `(channels, samples)` torch tensor.

```python
from pyannote.audio import Audio
from pyannote.core import Segment

audio = Audio(sample_rate=16000, mono="downmix")
waveform, sr = audio.crop({"audio": "file.wav"}, Segment(1.0, 5.0))
```

Source: `src/pyannote/audio/core/io.py`

## Low-level inference

### `Inference.__call__(file)`

Run a model on a file using sliding-window inference. Returns a `pyannote.core.SlidingWindowFeature` — a numpy array with associated time axis.

Used internally by pipelines. The CLI wrapper should prefer `pipeline(file)` over calling `Inference` directly unless doing custom post-processing.

```python
from pyannote.audio import Inference, Model

model = Model.from_pretrained("pyannote/segmentation-3.0")
inference = Inference(model, batch_size=32)
output = inference("audio.wav")  # SlidingWindowFeature
```

Source: `src/pyannote/audio/core/inference.py`

## Helper used by the CLI

The CLI's `__main__.py` defines a `get_diarization(prediction)` helper that normalizes both `Annotation` and `DiarizeOutput` returns into an `Annotation`:

```python
def get_diarization(prediction) -> Annotation:
    if isinstance(prediction, Annotation):
        return prediction
    if hasattr(prediction, "speaker_diarization"):
        return prediction.speaker_diarization
    raise ValueError("Could not find speaker diarization in prediction.")
```

The CLI wrapper should use the same pattern.

Source: `src/pyannote/audio/core/__main__.py`

## Sources

- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\core\pipeline.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\core\inference.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\core\io.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\pipelines\speaker_diarization.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\__main__.py`
