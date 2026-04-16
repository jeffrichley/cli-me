---
name: qwen3-tts
description: Text-to-speech generation, voice cloning, and voice design using Qwen3-TTS.
  Wraps the qwen-tts Python API for headless agent use. Use when asked to "generate
  speech", "text to speech", "TTS", "clone voice", "voice cloning", "design a voice",
  "create voiceover", "narrate", "read aloud", "synthesize speech", or "fine-tune TTS".
---

# Qwen3-TTS — cli-me skill

CLI-powered interface for Qwen3-TTS text-to-speech. This skill wraps the qwen-tts
Python API directly — it loads the model in-process for GPU-accelerated generation.

> **Note:** qwen3-tts generates speech from text. For extracting or processing
> existing audio files, use the ffmpeg or demucs skills.

## Prerequisites

- Python 3.12+
- `pip install qwen-tts` (installed automatically via uv)
- GPU recommended (CUDA). Falls back to CPU with a warning.
- Optional: `pip install flash-attn` for faster inference
- Optional: ffmpeg for non-WAV output formats

## CLI Commands

Run commands from the skill scripts directory:
```bash
cd <skill-dir>/scripts
uv run qwen3_tts_cli.py <group> <command> [options]
```

Or from any directory:
```bash
uv run --project <skill-dir>/scripts <skill-dir>/scripts/qwen3_tts_cli.py <group> <command> [options]
```

### Command Groups

| Group | Description |
|-------|-------------|
| `generate` | Text-to-speech with built-in speakers and style control |
| `clone` | Voice cloning from 3+ seconds of reference audio |
| `design` | Voice creation from natural language descriptions |
| `info` | Inspect speakers, languages, and hardware |
| `finetune` | Custom voice model training pipeline |

### Quick Examples

```bash
# Basic text-to-speech
uv run qwen3_tts_cli.py generate text "Hello world" --speaker Aiden -o hello.wav

# With style instruction
uv run qwen3_tts_cli.py generate text "I can't believe it!" --speaker Aiden --instruct "Speak with excitement" -o excited.wav

# Voice cloning
uv run qwen3_tts_cli.py clone text "Now I sound like you" --reference voice.wav --ref-text "This is the reference transcript" -o cloned.wav

# Voice design
uv run qwen3_tts_cli.py design text "Good morning" --description "A warm, deep male voice with a calm tone" -o designed.wav

# List speakers
uv run qwen3_tts_cli.py info speakers --pretty

# List supported languages
uv run qwen3_tts_cli.py info languages

# Check GPU status
uv run qwen3_tts_cli.py info device

# Fine-tune preparation
uv run qwen3_tts_cli.py finetune prepare --audio-dir ./samples/ --output-dir ./dataset/

# Fine-tune training
uv run qwen3_tts_cli.py finetune train --dataset ./dataset/train.jsonl --output-dir ./my-voice/

# Generate with fine-tuned model
uv run qwen3_tts_cli.py finetune generate "Hello" --model-dir ./my-voice/ -o finetuned.wav
```

### Common Task Mapping

| Task | Command | Notes |
|------|---------|-------|
| Generate speech | `generate text "..." --speaker Aiden -o out.wav` | 9 built-in speakers available |
| Generate with emotion | `generate text "..." --instruct "whisper softly" -o out.wav` | Natural language style control |
| Clone a voice | `clone text "..." --reference ref.wav --ref-text "transcript" -o out.wav` | 3+ seconds clean reference audio |
| Design a voice | `design text "..." --description "young female, cheerful" -o out.wav` | Requires `--model 1.7b`; no 0.6B VoiceDesign model exists |
| List speakers | `info speakers --pretty` | JSON by default |
| Check hardware | `info device` | Shows GPU/CPU and VRAM |
| Use smaller model | `generate text "..." --model 0.6b -o out.wav` | Lower VRAM, faster, slightly lower quality |
| Output as MP3 | `generate text "..." --format mp3 -o out.mp3` | Requires ffmpeg installed |

### Default Behavior

- **Model:** Qwen3-TTS-12Hz-1.7B-CustomVoice (quality). Use `--model 0.6b` for speed.
- **GPU:** Auto-detected. CUDA > MPS > CPU. Use `--device cpu` to force CPU.
- **Output:** WAV at 24kHz. Use `--format mp3|flac|ogg` for conversion (requires ffmpeg).
- **Language:** Auto-detected. Use `--lang English` to force a specific language.
- **Timeouts:** Model loading takes 30-60 seconds on first run (downloads ~3.4GB).
  Use `timeout: 600000` for Bash tool calls. Consider running in background for long text.

## Knowledge Base

Read technique guides and best practices from the `references/` directory.
Start with `references/index.md` for a table of contents.

When you need to understand how something works under the hood, check
`references/source-analysis/`.

## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Log what you did: `clime log append --skill qwen3-tts --message "<what you did and learned>" --log-file references/log.md`
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
