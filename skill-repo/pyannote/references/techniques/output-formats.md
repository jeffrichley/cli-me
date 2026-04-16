# Output Formats

How to read, write, and convert between pyannote's output formats. The central data structure is the `Annotation` object. From there you can export to RTTM, JSON, or plain text.

## The Annotation Object

`Annotation` is pyannote's core output type. It maps time segments to speaker labels.

```python
from pyannote.core import Annotation, Segment

# An Annotation is returned by pipeline() calls
# You can also build one manually
annotation = Annotation()
annotation[Segment(0.5, 2.3)] = "SPEAKER_00"
annotation[Segment(2.8, 5.1)] = "SPEAKER_01"
annotation[Segment(5.5, 7.0)] = "SPEAKER_00"

# List all unique speaker labels
print(annotation.labels())  # ['SPEAKER_00', 'SPEAKER_01']

# Iterate over all segments
for segment, track, label in annotation.itertracks(yield_label=True):
    print(f"{segment.start:.3f} --> {segment.end:.3f}  {label}")

# Get the temporal support (union of all segments)
support = annotation.get_timeline().support()
for seg in support:
    print(f"Active: {seg.start:.3f} --> {seg.end:.3f}")
```

## RTTM Format

RTTM (Rich Transcription Time Mark) is the standard diarization output format.

### Writing RTTM

```python
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token=os.environ["HF_TOKEN"]
)
output = pipeline("audio.wav")

# Write to file
with open("output.rttm", "w") as f:
    output.speaker_diarization.write_rttm(f)
```

### RTTM Line Format

```
SPEAKER <file_id> <channel> <start_sec> <duration_sec> <NA> <NA> <speaker_label> <NA> <NA>
```

Example:
```
SPEAKER audio 1 0.500 1.800 <NA> <NA> SPEAKER_00 <NA> <NA>
SPEAKER audio 1 2.800 2.300 <NA> <NA> SPEAKER_01 <NA> <NA>
SPEAKER audio 1 5.500 1.500 <NA> <NA> SPEAKER_00 <NA> <NA>
```

Fields:
- Field 1: always `SPEAKER`
- Field 2: file identifier (stem of the audio filename)
- Field 3: channel (always `1`)
- Field 4: start time in seconds
- Field 5: duration in seconds (not end time)
- Fields 6–7: `<NA>` (unused)
- Field 8: speaker label
- Fields 9–10: `<NA>` (unused)

### Reading RTTM Back

```python
from pyannote.core import Annotation, Segment

def read_rttm(rttm_path):
    annotation = Annotation()
    with open(rttm_path) as f:
        for line in f:
            parts = line.strip().split()
            if not parts or parts[0] != "SPEAKER":
                continue
            start = float(parts[3])
            duration = float(parts[4])
            speaker = parts[7]
            annotation[Segment(start, start + duration)] = speaker
    return annotation

annotation = read_rttm("output.rttm")
```

## JSON via serialize()

```python
import json

output = pipeline("audio.wav")
data = output.serialize()

# Pretty-print
print(json.dumps(data, indent=2))
```

Output structure:
```json
{
  "diarization": [
    {"start": 0.5,  "end": 2.3,  "speaker": "SPEAKER_00"},
    {"start": 2.8,  "end": 5.1,  "speaker": "SPEAKER_01"},
    {"start": 5.5,  "end": 7.0,  "speaker": "SPEAKER_00"}
  ],
  "exclusive_diarization": [
    {"start": 0.5,  "end": 2.3,  "speaker": "SPEAKER_00"},
    {"start": 2.8,  "end": 5.1,  "speaker": "SPEAKER_01"},
    {"start": 5.5,  "end": 7.0,  "speaker": "SPEAKER_00"}
  ]
}
```

The `"diarization"` key contains all speaker turns (including overlapping speech). The `"exclusive_diarization"` key contains the same turns with overlaps resolved so each time point has at most one speaker.

### Parsing JSON Output

```python
import json
from pyannote.core import Annotation, Segment

with open("output.json") as f:
    data = json.load(f)

annotation = Annotation()
for entry in data["diarization"]:
    seg = Segment(entry["start"], entry["end"])
    annotation[seg] = entry["speaker"]
```

## Timeline and Segment Objects

```python
from pyannote.core import Segment, Timeline

# Segment: a time interval
seg = Segment(1.5, 4.2)
print(seg.start, seg.end, seg.duration)  # 1.5, 4.2, 2.7

# Timeline: ordered list of non-overlapping segments
timeline = Timeline([
    Segment(0.5, 2.0),
    Segment(3.0, 5.5),
])

# Merge overlapping/adjacent segments
merged = timeline.support()

# Crop to a region of interest
roi = Segment(1.0, 4.0)
cropped = timeline.crop(roi)
```

## Cropping an Annotation

```python
from pyannote.core import Segment

# Keep only a time window
window = Segment(10.0, 30.0)
cropped_annotation = annotation.crop(window)

# Crop mode options:
# "intersection" (default): keep only the part within the window
# "loose": keep any segment that overlaps with the window
cropped = annotation.crop(window, mode="loose")
```

## Converting Between Formats

### Annotation to plain text

```python
def annotation_to_tsv(annotation, filepath):
    with open(filepath, "w") as f:
        f.write("start\tend\tspeaker\n")
        for segment, _, label in annotation.itertracks(yield_label=True):
            f.write(f"{segment.start:.3f}\t{segment.end:.3f}\t{label}\n")
```

### Annotation to SRT-like format

```python
def annotation_to_srt(annotation, filepath):
    with open(filepath, "w") as f:
        for i, (segment, _, label) in enumerate(
            annotation.itertracks(yield_label=True), start=1
        ):
            def fmt(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s = t % 60
                return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

            f.write(f"{i}\n")
            f.write(f"{fmt(segment.start)} --> {fmt(segment.end)}\n")
            f.write(f"[{label}]\n\n")
```

### Annotation statistics

```python
from collections import defaultdict

# Duration per speaker
durations = defaultdict(float)
for segment, _, label in annotation.itertracks(yield_label=True):
    durations[label] += segment.duration

for speaker, duration in sorted(durations.items()):
    print(f"{speaker}: {duration:.1f}s")
```

## Gotchas

- **RTTM uses duration, not end time**: `start + duration = end`. Don't confuse the fields when reading/writing manually.
- **Multiple tracks per segment**: Annotation supports overlapping speech with track IDs. `itertracks()` returns `(segment, track, label)`. The track ID distinguishes overlapping segments for the same time region.
- **serialize() is DiarizeOutput-specific**: it lives on the pipeline output object, not on bare `Annotation` objects. Use `write_rttm()` on a bare Annotation.

## Sources

- pyannote.audio GitHub: https://github.com/pyannote/pyannote-audio
- pyannote.core source (Annotation): https://github.com/pyannote/pyannote-core
- RTTM format specification: NIST RT evaluations (search "NIST RT evaluation RTTM format" for the spec)
- HuggingFace pyannote models: https://huggingface.co/pyannote
