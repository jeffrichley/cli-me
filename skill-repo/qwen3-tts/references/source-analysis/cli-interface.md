---
title: CLI Interface
tags: [source-analysis, qwen3-tts]
sources: [https://github.com/QwenLM/Qwen3-TTS]
created: 2026-04-16
updated: 2026-04-16
---

# CLI Interface

## Qwen3-TTS Has No Native Scriptable CLI

The `qwen-tts` package (v0.1.1) ships exactly one CLI entry point:

```
qwen-tts-demo  →  qwen_tts.cli.demo:main
```

This is a **Gradio web UI demo**, not a scriptable command-line tool. Its purpose is
to launch a browser-based interface for manual interactive use:

```bash
qwen-tts-demo Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --ip 0.0.0.0 --port 8000
```

It accepts `--ssl-certfile`, `--ssl-keyfile`, `--no-ssl-verify` for HTTPS.
It is **not suitable** for programmatic batch use or piping output.

## Third-Party CLI Packages

There is a `qwen-tts-cli` package on PyPI. This is a **third-party package**, not
maintained by the Qwen team, and is not part of the official `qwen-tts` distribution.
It is not analyzed here and we do not wrap it.

## How Our Skill Works

Our `/qwen3-tts` skill wraps the **Python API directly** via `Qwen3TTSModel`:

```python
from qwen_tts import Qwen3TTSModel
```

The skill's backend module handles model loading, argument parsing, and file I/O.
There is no subprocess invocation of any CLI binary.

This is the correct approach because:
1. The official package provides no CLI for programmatic use
2. Wrapping the Python API gives us full control over inputs and outputs
3. We can leverage all generation kwargs not exposed in any GUI
