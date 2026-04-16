# API Surface

Python API for pyannote.audio 4.0.4. All entries verified against source at commit 78c0d16.

## Loading pipelines and models

### `Pipeline.from_pretrained(checkpoint, token=None, cache_dir=None, revision=None)`

The primary entry point. Loads a pretrained pipeline from a HuggingFace model hub checkpoint or a local YAML config file.

```python
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token="hf_...",
    cache_dir="/path/to/cache",
)
```

Returns `None` if the pipeline cannot be loaded (caller must check).

### `Model.from_pretrained(checkpoint)`

Load a neural network model (not a full pipeline). Used when you need raw inference rather than a high-level pipeline.

```python
from pyannote.audio import Model
model = Model.from_pretrained("pyannote/segmentation-3.0")
```

## Running pipelines

### `pipeline(audio_file, **kwargs)`

Apply the loaded pipeline to an audio file. The file can be a path string, a `pathlib.Path`, or a dict with an `"audio"` key.

Returns either an `Annotation` (for VAD, simple diarization) or a `DiarizeOutput` dataclass (for `SpeakerDiarization`).

For `SpeakerDiarization`, key kwargs:

```python
output = pipeline(
    "audio.wav",
    num_speakers=2,       # fix speaker count (optional)
    min_speakers=1,       # lower bound (optional)
    max_speakers=5,       # upper bound (optional)
    return_embeddings=True,  # include speaker embeddings in output
)
```

### `pipeline.to(device)`

Move the pipeline (and all its models) to a torch device.

```python
import torch
pipeline.to(torch.device("cuda"))
```

## Audio I/O

### `Audio(sample_rate=16000, mono='downmix')`

Reads and pre-processes audio files.

```python
from pyannote.audio import Audio
audio = Audio(sample_rate=16000, mono="downmix")

# Get duration without loading waveform
duration = audio.get_duration({"audio": "file.wav"})

# Load a segment
waveform, sample_rate = audio.crop({"audio": "file.wav"}, segment)
```

## Inference

### `Inference(model, duration=None, step=None, batch_size=32, device=None)`

Runs a model on a file with a sliding window, handles batching and overlap-add aggregation.

```python
from pyannote.audio import Inference
inference = Inference(model, duration=5.0, step=0.5, batch_size=32)
output = inference("audio.wav")  # returns SlidingWindowFeature
```

Additional constructor parameters:
- `window` — `"sliding"` (default) or `"whole"`
- `pre_aggregation_hook` — callable applied before overlap-add
- `skip_aggregation` — return raw chunks instead of aggregated output
- `skip_conversion` — skip powerset-to-multilabel conversion

## Speaker embeddings

### `PretrainedSpeakerEmbedding`

Extracts speaker embeddings. Supports multiple backends: pyannote, SpeechBrain, NeMo, ONNX.

```python
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
embedding = PretrainedSpeakerEmbedding("speechbrain/spkrec-ecapa-voxceleb")
```

## Output types

### `Annotation` (from `pyannote.core`)

Standard output for VAD, simple diarization, and multi-label segmentation.

Key methods:
- `write_rttm(file)` — write RTTM format to a file object
- `itertracks(yield_label=True)` — iterate `(segment, track, label)` tuples
- `labels()` — list unique speaker labels
- `support()` — merge overlapping segments into a `Timeline`
- `crop(segment)` — restrict annotation to a time segment

### `DiarizeOutput` (from `pyannote.audio.pipelines.speaker_diarization`)

Dataclass returned by `SpeakerDiarization` pipeline.

Fields:
- `speaker_diarization: Annotation` — full diarization including overlapping speech
- `exclusive_speaker_diarization: Annotation` — non-overlapping version, suitable for downstream transcription
- `speaker_embeddings: np.ndarray | None` — shape `(num_speakers, dimension)`, ordered by `speaker_diarization.labels()`

Methods:
- `serialize() -> dict` — JSON-serializable dict with `diarization`, `exclusive_diarization`, and optionally `embeddings` keys

## Pipeline types

| Class | Location | Purpose |
|---|---|---|
| `SpeakerDiarization` | `pipelines/speaker_diarization.py` | Who speaks when, with clustering |
| `VoiceActivityDetection` | `pipelines/voice_activity_detection.py` | Speech vs. silence |
| `SpeakerVerification` | `pipelines/speaker_verification.py` | Is it the same speaker? |
| `SpeechSeparation` | `pipelines/speech_separation.py` | Separate overlapping speech |
| `MultiLabelSegmentation` | `pipelines/multilabel.py` | Multi-class audio segmentation |

## Sources

- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\core\pipeline.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\core\inference.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\core\io.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\core\model.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\pipelines\speaker_diarization.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\pipelines\speaker_verification.py`
