# pyannote Skill Wiki

Agent-native CLI wrapper for pyannote.audio — speaker diarization, voice activity
detection, speaker verification, and embedding extraction.

## Source Analysis

- [Analyzed Version](source-analysis/analyzed-version.md) — pyannote.audio 4.0.4, commit 78c0d16
- [API Surface](source-analysis/api-surface.md) — Python API: Pipeline, Audio, Inference, Model
- [CLI Interface](source-analysis/cli-interface.md) — pyannote-audio CLI commands and flags
- [Internal Architecture](source-analysis/internal-architecture.md) — package structure, data flow
- [Key Functions](source-analysis/key-functions.md) — functions the CLI wrapper invokes

## Techniques

- [Speaker Diarization](techniques/speaker-diarization.md) — "who spoke when" pipeline
- [Voice Activity Detection](techniques/voice-activity-detection.md) — speech region detection
- [Speaker Verification](techniques/speaker-verification.md) — same-speaker comparison
- [Embedding Extraction](techniques/embedding-extraction.md) — speaker embedding vectors
- [Output Formats](techniques/output-formats.md) — RTTM, JSON, Annotation objects
- [Configuration & Setup](techniques/configuration-and-setup.md) — HF token, devices, caching
- [Batch Processing](techniques/batch-processing.md) — multi-file processing patterns

## Operational

- [Log](log.md) — append-only build log
- [Gotchas](gotchas.md) — known issues and workarounds
- [Testing](testing.md) — three-tier test strategy, real-speech fixture setup
