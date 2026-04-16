# Internal Architecture

Architecture of pyannote.audio 4.0.4 (commit 78c0d16). Based on direct source inspection.

## Package layout

```
src/pyannote/audio/
├── __init__.py           # public API: Audio, Model, Pipeline, Inference
├── __main__.py           # CLI entry point (typer app)
├── core/                 # base classes
│   ├── model.py          # Model base class
│   ├── pipeline.py       # Pipeline base class + from_pretrained()
│   ├── inference.py      # Inference sliding-window runner
│   ├── io.py             # Audio I/O class
│   ├── task.py           # Task base class (training)
│   ├── plda.py           # PLDA scoring
│   └── calibration.py    # score calibration
├── models/               # neural network architectures
│   ├── segmentation/
│   │   ├── PyanNet.py    # recurrent segmentation model
│   │   └── SSeRiouSS.py  # transformer segmentation model
│   ├── embedding/
│   │   ├── xvector.py    # x-vector speaker embedding
│   │   └── wespeaker/    # WeSpeaker embedding models
│   └── separation/
│       └── ToTaToNet.py  # speech separation model
├── pipelines/            # high-level task pipelines
│   ├── speaker_diarization.py    # SpeakerDiarization
│   ├── voice_activity_detection.py  # VoiceActivityDetection
│   ├── speaker_verification.py   # SpeakerVerification + PretrainedSpeakerEmbedding
│   ├── speech_separation.py      # SpeechSeparation
│   ├── multilabel.py             # MultiLabelSegmentation
│   ├── clustering.py             # BaseClustering, AgglomerativeClustering, VBxClustering
│   └── pyannoteai/               # pyannote.ai API integration
├── tasks/                # training task definitions
├── augmentation/         # data augmentation for training
├── torchmetrics/         # custom training metrics
├── telemetry/            # usage telemetry
└── utils/                # shared helpers
```

## Core data flow for speaker diarization

```
Audio file
    |
    v
Audio (io.py)          — load waveform, resample, downmix
    |
    v
Inference (inference.py) — sliding window over waveform, batch processing
    |
    v
Segmentation model     — PyanNet or SSeRiouSS
(powerset multi-class output per frame)
    |
    v
Binarization           — powerset -> multi-label, threshold
    |
    v
Embedding extraction   — PretrainedSpeakerEmbedding per speech segment
    |
    v
Clustering             — AgglomerativeClustering / VBxClustering / HierarchicalClustering
(optionally uses PLDA scoring)
    |
    v
Annotation             — speaker turns mapped to final speaker labels
    |
    v
DiarizeOutput          — .speaker_diarization, .exclusive_speaker_diarization, .speaker_embeddings
```

## Key design patterns

### Pipeline configuration (YAML)

Pipelines are configured via YAML files with four top-level sections:

```yaml
pipeline:
  name: pyannote.audio.pipelines.SpeakerDiarization
  params:
    segmentation: pyannote/segmentation-3.0
    embedding: pyannote/wespeaker-voxceleb-resnet34-LM

params:
  clustering: AgglomerativeClustering
  segmentation_batch_size: 32
  embedding_batch_size: 32
  embedding_exclude_overlap: true
  clustering.method: centroid
  clustering.threshold: 0.753

freeze: {}

preprocessors: {}
```

### `Pipeline.from_pretrained()` resolution

1. If the argument is a local path to a YAML file, loads it directly.
2. Otherwise, downloads the config and associated model checkpoints from HuggingFace Hub.
3. Expands `$model/{subfolder}` references within the config to resolve nested model downloads.
4. Instantiates the pipeline class named in `pipeline.name`.
5. Applies `params` and `freeze` sections.

### Sliding window inference

`Inference` runs a model on overlapping chunks of audio and recombines the outputs using overlap-add aggregation. Key parameters:
- `duration` — chunk length in seconds (defaults to training duration)
- `step` — stride between chunks (defaults to warm-up duration or 10% of duration)
- `batch_size` — number of chunks processed together on the GPU

### Training framework

Training is built on PyTorch Lightning. Each `Task` subclass defines:
- dataset preparation and augmentation
- loss function and metrics
- what the model learns to predict (segmentation, embedding, separation)

Hyperparameter optimization uses Optuna via `pyannote.pipeline.optimizer.Optimizer`.

## External dependencies (key ones)

| Dependency | Role |
|---|---|
| PyTorch | neural network runtime |
| PyTorch Lightning | training loop |
| pyannote.core | Annotation, Timeline, Segment primitives |
| pyannote.database | dataset/protocol abstraction |
| pyannote.pipeline | Pipeline base class, Optuna optimizer |
| pyannote.metrics | DER, JER evaluation |
| huggingface_hub | model downloading |
| einops | tensor reshaping |
| typer | CLI framework |
| rich | progress display |
| scipy | clustering, scalar optimization |
| scikit-learn | KMeans |

## Sources

- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\core\pipeline.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\core\inference.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\pipelines\speaker_diarization.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\pipelines\clustering.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\__main__.py`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\models\`
- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\pyproject.toml`
