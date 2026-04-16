# Configuration and Setup

Setup, configuration, and performance tuning for pyannote.audio. Covers authentication, device selection, batch size tuning, offline mode, and common installation gotchas.

## HuggingFace Token

Most pyannote models are gated — they require a HuggingFace account and explicit acceptance of the model's terms.

### Step 1: Accept the model terms

Visit each model page and click "Agree and access repository":
- https://huggingface.co/pyannote/speaker-diarization-community-1
- https://huggingface.co/pyannote/voice-activity-detection
- https://huggingface.co/pyannote/segmentation-3.0
- https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM

### Step 2: Create an access token

Go to https://huggingface.co/settings/tokens and create a **read** token.

### Step 3: Provide the token

```bash
# Recommended: set as environment variable
export HF_TOKEN=hf_your_token_here
```

```python
import os

# In code — reads from environment
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token=os.environ["HF_TOKEN"]
)

# Or pass directly (avoid hardcoding in scripts)
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token="hf_your_token_here"
)
```

The cli-me skill accepts `--token` to pass the token explicitly, falling back to `HF_TOKEN` if not provided.

## Device Selection

pyannote runs on CPU by default. Use GPU for significant speedups.

```python
import torch
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token=os.environ["HF_TOKEN"]
)

# Auto-detect best available device
def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")  # Apple Silicon
    return torch.device("cpu")

pipeline.to(get_device())
output = pipeline("audio.wav")
```

### Device performance comparison (approximate, 60-minute audio)

| Device         | Processing time |
|---------------|----------------|
| CPU (8-core)  | ~15–20 min     |
| NVIDIA GPU    | ~1–3 min       |
| Apple M-series| ~3–6 min       |

## Batch Size Tuning

Larger batch sizes improve GPU throughput at the cost of VRAM.

```python
# Increase for faster GPU processing
pipeline.segmentation_batch_size = 32
pipeline.embedding_batch_size = 32

# Decrease if you get CUDA out-of-memory errors
pipeline.segmentation_batch_size = 4
pipeline.embedding_batch_size = 4
```

### Recommended batch sizes by VRAM

| VRAM  | segmentation_batch_size | embedding_batch_size |
|-------|------------------------|---------------------|
| 4 GB  | 8                      | 8                   |
| 8 GB  | 16                     | 16                  |
| 16 GB | 32                     | 32                  |
| 24 GB | 64                     | 64                  |

## Memory Requirements

Approximate GPU VRAM requirements:

| Component           | VRAM     |
|--------------------|----------|
| Segmentation model | ~1 GB    |
| Embedding model    | ~0.5 GB  |
| Full diarization pipeline | ~1.5–2 GB (both loaded) |

CPU RAM: typically 2–4 GB for a full pipeline plus audio data.

## Model Cache and Offline Mode

Models are cached in `~/.cache/huggingface/hub/` after first download.

```python
# First run: downloads models (may take several minutes on slow connections)
# Subsequent runs: loads from cache instantly

# To pre-download without running inference:
from huggingface_hub import snapshot_download

snapshot_download(
    "pyannote/speaker-diarization-community-1",
    token=os.environ["HF_TOKEN"]
)
```

```bash
# Force offline mode (prevents any network calls)
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
```

## Pipeline YAML Configuration

pyannote pipelines can be configured via YAML. This is how hyperparameters like clustering threshold are stored.

```yaml
# Example pipeline config (usually in ~/.cache/huggingface/...)
pipeline:
  name: pyannote.audio.pipelines.SpeakerDiarization
  params:
    embedding: pyannote/wespeaker-voxceleb-resnet34-LM
    embedding_batch_size: 32
    embedding_exclude_overlap: true
    segmentation: pyannote/segmentation-3.0
    segmentation_batch_size: 32

params:
  clustering: AgglomerativeClustering
  embedding_exclude_overlap: true
  min_cluster_size: 15
  min_duration_off: 0.0
  min_duration_on: 0.0
  onset: 0.5
  offset: 0.5
```

To instantiate from a local YAML:

```python
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "/path/to/config.yaml",
    token=os.environ["HF_TOKEN"]
)
```

## pyannote-audio CLI Location

The `pyannote-audio` executable is **not on the system PATH** by default when installed with `pip install --user`.

On Windows, it is installed at:
```
C:\Users\jeffr\AppData\Roaming\Python\Python313\Scripts\pyannote-audio.exe
```

The cli-me skill uses the Python API directly (`from pyannote.audio import Pipeline`) to avoid this issue entirely. If you need the CLI directly:

```bash
# Windows — run with full path
"C:/Users/jeffr/AppData/Roaming/Python/Python313/Scripts/pyannote-audio.exe" --help

# Or add to PATH in your shell config
export PATH="$PATH:/c/Users/jeffr/AppData/Roaming/Python/Python313/Scripts"
```

## Installation

```bash
pip install pyannote.audio

# With GPU support (CUDA 12.x)
pip install pyannote.audio torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Verifying Setup

```python
import pyannote.audio
import torch

print(f"pyannote.audio version: {pyannote.audio.__version__}")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"MPS available: {torch.backends.mps.is_available()}")

# Quick token check
from huggingface_hub import HfApi
api = HfApi()
user = api.whoami(token=os.environ.get("HF_TOKEN"))
print(f"HF user: {user['name']}")
```

## Gotchas

- **First run is always slow**: model weights (~500MB for diarization) are downloaded on first use. Budget 2–5 minutes on a fast connection. Subsequent runs load from cache.
- **Token errors at runtime, not at load time**: `Pipeline.from_pretrained()` may succeed even with an invalid token. The 401 error surfaces when the pipeline first tries to download the model weights.
- **pyannote.audio requires Python 3.8+** and PyTorch 2.0+. Older environments may have silent compatibility issues.
- **Windows path issues**: use forward slashes or raw strings for paths. `"C:/Users/..."` works; `"C:\Users\..."` may cause issues.

## Sources

- pyannote.audio GitHub: https://github.com/pyannote/pyannote-audio
- HuggingFace token settings: https://huggingface.co/settings/tokens
- pyannote model hub: https://huggingface.co/pyannote
- PyTorch installation: https://pytorch.org/get-started/locally/
