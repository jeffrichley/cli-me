# CLI Interface

All commands verified against the installed binary (`pyannote-audio.exe`) and source at commit 78c0d16.

## Binary location

```
C:/Users/jeffr/AppData/Roaming/Python/Python313/Scripts/pyannote-audio.exe
```

This path is not on PATH by default. The CLI wrapper must invoke it with the full path or invoke Python with `-m pyannote.audio`.

## Commands

### `apply` — apply a pipeline to audio

```
pyannote-audio apply PIPELINE AUDIO [TOKEN] [OPTIONS]
```

Applies a pretrained pipeline to a single audio file or a directory of audio files. Writes results as RTTM (always) and JSON (when the pipeline supports serialization).

Arguments:
- `PIPELINE` — HuggingFace model ID (e.g. `pyannote/speaker-diarization-3.1`) or path to a local YAML config
- `AUDIO` — path to an audio file or directory
- `TOKEN` — HuggingFace token (positional, optional)

Options:
- `--into PATH` — output file or directory; if omitted, RTTM is written to stdout
- `--revision TEXT` — specific pipeline revision to load
- `--token TEXT` — HuggingFace token (alternative to positional)
- `--cache PATH` — local cache directory for downloaded files
- `--device {cpu|cuda|mps|auto}` — accelerator; `auto` selects CUDA > MPS > CPU (default: `auto`)

When `AUDIO` is a directory, `INTO` must also be a directory. Output files are named `{stem}.rttm` and `{stem}.json`.

### `download` — download a pipeline for offline use

```
pyannote-audio download PIPELINE [TOKEN] [OPTIONS]
```

Downloads and caches a pretrained pipeline without applying it. Useful for pre-staging models before offline use.

Arguments:
- `PIPELINE` — HuggingFace model ID or local YAML path
- `TOKEN` — HuggingFace token (positional, optional)

Options:
- `--revision TEXT` — specific pipeline revision
- `--cache PATH` — local cache directory

### `optimize` — optimize pipeline hyperparameters

```
pyannote-audio optimize PIPELINE PROTOCOL [OPTIONS]
```

Runs Optuna-based hyperparameter optimization against a pyannote.database protocol. The pipeline YAML config file is updated in-place with the best parameters found.

Arguments:
- `PIPELINE` — path to a local pipeline YAML config file (must be writable)
- `PROTOCOL` — pyannote.database protocol name (e.g. `AMI.SpeakerDiarization.MixHeadset`)

Options:
- `--subset {train|development|test}` — dataset split to optimize on (default: `development`)
- `--device {cpu|cuda|mps|auto}` — accelerator (default: `auto`)
- `--registry PATH` — path to a pyannote.database registry YAML
- `--max-iterations INT` — stop after N iterations; omit to run indefinitely
- `--num-speakers {oracle|auto}` — whether to pass ground-truth speaker count (default: `auto`)
- `--metric {DiarizationErrorRate|JaccardErrorRate}` — metric to minimize (default: `DiarizationErrorRate`)

Optimization state is stored in a `.journal` file alongside the YAML. Best results are saved as `{pipeline}.{protocol}.{subset}.yaml`.

### `benchmark` — benchmark a pipeline on a dataset

```
pyannote-audio benchmark PIPELINE PROTOCOL INTO [TOKEN] [OPTIONS]
```

Runs a pipeline on all files in a protocol subset and computes DER. Saves RTTM, JSON, CSV, and timing results.

Arguments:
- `PIPELINE` — HuggingFace model ID
- `PROTOCOL` — pyannote.database protocol name
- `INTO` — directory where results are saved (must exist)
- `TOKEN` — HuggingFace token (positional, optional)

Options:
- `--subset {train|development|test}` — dataset split (default: `test`)
- `--revision TEXT` — pipeline revision
- `--token TEXT` — HuggingFace token (flag alternative)
- `--cache PATH` — local cache directory
- `--device {cpu|cuda|mps|auto}` — accelerator (default: `auto`)
- `--registry PATH` — pyannote.database registry file
- `--num-speakers {oracle|auto}` — speaker count mode (default: `auto`)
- `--optimize / --no-optimize` — also compute post-processed results with optimized `min_duration_off` (default: no)
- `--progress / --no-progress` — show progress bar (default: no)
- `--per-file / --no-per-file` — save one RTTM/JSON per file instead of a single combined file (default: no)

Output files written to `INTO`:
- `{protocol}.{subset}.rttm` — diarization predictions
- `{protocol}.{subset}.json` — serialized predictions (if supported)
- `{protocol}.{subset}.csv` / `.txt` — DER report
- `{protocol}.{subset}.yml` — processing time and speed metrics
- `{protocol}.{subset}.SpeakerCount.csv` — speaker count confusion matrix

### `strip` — strip a checkpoint for inference

```
pyannote-audio strip CHECKPOINT INTO
```

Removes training-only data from a model checkpoint, keeping only the weights and metadata needed for inference. The stripped checkpoint is verified to load correctly before saving.

Arguments:
- `CHECKPOINT` — path to a full `.ckpt` file
- `INTO` — output path for the stripped checkpoint

Keys retained: `pytorch-lightning_version`, `hparams_name`, `hyper_parameters`, `state_dict`, `pyannote.audio`.

## Sources

- `E:\workspaces\tools\cli-me\tmp\source-analysis\pyannote\src\pyannote\audio\__main__.py`
