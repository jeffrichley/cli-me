---
title: Fine-tuning a Custom Speaker
tags: [technique, qwen3-tts, fine-tuning, training]
sources: [https://github.com/QwenLM/Qwen3-TTS]
created: 2026-04-16
updated: 2026-04-16
---

# Fine-tuning a Custom Speaker

## When to Use

- You want a custom speaker that can be invoked by name using `generate_custom_voice`, rather than requiring a reference audio on every call
- You have a substantial corpus of audio from a single speaker (dozens to hundreds of recordings) and want the model to internalize that voice
- You need a custom voice that responds to `instruct` style guidance (voice cloning does not support `instruct`)
- You are building a production system where re-encoding reference audio on each call is not acceptable

## Technique

Fine-tuning adapts the Base model to a new speaker using supervised fine-tuning (SFT). After training, the resulting checkpoint behaves like a CustomVoice model — invoke it with `generate_custom_voice` using the speaker name you specified during training.

**Important: the CLI wrapper is a preparation and orchestration aid, not a training runner.** The `finetune prepare` subcommand validates your audio files. The `finetune train` subcommand builds the argument list for the upstream training script. You must run the actual training scripts from the upstream Qwen3-TTS repository.

**Full pipeline:**

### Step 1: Prepare your audio dataset

Collect clean, single-speaker WAV recordings. Each recording needs:
- A matching text transcript (exact match to the audio content)
- A reference audio clip from the same speaker (can be any clip from the corpus)

Organize into a JSONL file where each line has:
```json
{"audio": "path/to/utterance.wav", "text": "transcript of utterance", "ref_audio": "path/to/any_speaker_sample.wav"}
```

### Step 2: Validate audio files with `finetune prepare`

```bash
uv run python -m qwen3_tts_cli finetune prepare \
  --audio-dir ./speaker_samples/ \
  --output-dir ./dataset/
```

This checks that WAV files exist and are accessible in `--audio-dir`. It does **not** generate JSONL or run codec encoding — it is a validation step only. Full dataset preparation (JSONL generation and codec encoding) requires the upstream `prepare_data.py` script.

### Step 3: Encode audio to codec tokens (`prepare_data.py`)

Run this upstream script directly:

```bash
python finetuning/prepare_data.py \
  --device cuda:0 \
  --tokenizer_model_path Qwen/Qwen3-TTS-Tokenizer-12Hz \
  --input_jsonl train_raw.jsonl \
  --output_jsonl train_with_codes.jsonl
```

This runs the 12Hz tokenizer over every audio file, converting raw waveforms to codec token sequences. The output JSONL adds encoded audio codes alongside the original fields. This is the most time-consuming preparation step.

### Step 4: Get training arguments with `finetune train`

```bash
uv run python -m qwen3_tts_cli finetune train \
  --dataset train_with_codes.jsonl \
  --output-dir ./my_speaker_checkpoints \
  --base-model 1.7b \
  --epochs 10 \
  --batch-size 32 \
  --learning-rate 2e-6
```

This prints the argument list that you should pass to the upstream `sft_12hz.py` training script. It does **not** run training itself. Copy the printed args and run the actual training via the upstream script.

### Step 5: Run supervised fine-tuning (`sft_12hz.py`)

Use the args from Step 4 to run the upstream training script directly:

```bash
python finetuning/sft_12hz.py \
  --init_model_path Qwen/Qwen3-TTS-12Hz-1.7B-Base \
  --output_model_path ./my_speaker_checkpoints \
  --train_jsonl train_with_codes.jsonl \
  --batch_size 32 \
  --num_epochs 10 \
  --speaker_name my_custom_speaker
```

Checkpoints are saved after each epoch as `my_speaker_checkpoints/checkpoint-epoch-N/` in HuggingFace format.

### Step 6: Use the fine-tuned model

```bash
uv run python -m qwen3_tts_cli finetune generate "Hello, I am your custom voice." \
  --model-dir ./my_speaker_checkpoints/checkpoint-epoch-10 \
  -o output.wav
```

**Hardware requirements:**

| Model    | Minimum VRAM (training) |
|----------|------------------------|
| 1.7B Base | 16GB+                 |
| 0.6B Base | 8GB+                  |

Training with `batch_size=32` on a single GPU requires the full VRAM allocation. Reduce `batch_size` if you run out of memory.

## Under the Hood

The SFT script trains the Base model's transformer weights to associate a new speaker token with the target speaker's codec patterns. The `speaker_name` argument becomes a new entry in the model's `supported_speakers` list.

Training objective: minimize cross-entropy loss over the codec token sequence, conditioned on the speaker embedding extracted from `ref_audio` by the ECAPA-TDNN encoder.

The fine-tuned checkpoint is saved in standard HuggingFace format, loadable directly with `Qwen3TTSModel.from_pretrained(path)`. The model type will be `custom_voice` in the saved config, enabling `generate_custom_voice`.

Only **single-speaker fine-tuning** is supported in this release. Multi-speaker fine-tuning is not available.

## Gotchas

- **`finetune prepare` is validation only.** It checks that WAV files exist but does not generate JSONL or run codec encoding. Use the upstream `prepare_data.py` for actual data preparation.
- **`finetune train` builds arguments but does not run training.** It prints the argument list for the upstream training script. You must run `sft_12hz.py` yourself.
- **Only the Base model can be fine-tuned.** VoiceDesign and CustomVoice models are not the correct starting point.
- **Only single-speaker fine-tuning is supported.** Do not attempt to add multiple speakers in one training run.
- **Transcripts must match audio exactly.** Errors in the JSONL transcripts will train the model on bad audio-text alignments, degrading quality.
- **16GB+ VRAM for 1.7B is a hard requirement at batch_size=32.** Lower batch sizes reduce memory but may hurt convergence quality.
- **Prepare step encodes every audio file.** This can take significant time for large datasets. Run it on a GPU for speed.
- After fine-tuning, use `generate_custom_voice` with your `speaker_name` — voice cloning methods no longer apply to this checkpoint.
- The `instruct` parameter works on fine-tuned 1.7B models (not 0.6B). Style guidance is available post fine-tuning.
- Fine-tuning does not improve multilingual coverage — it only adds a new speaker identity.

## Sources

- https://github.com/QwenLM/Qwen3-TTS (finetuning/ directory)
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base

## Learned from Usage

(No usage notes yet.)
