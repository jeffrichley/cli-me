---
title: Multilingual Speech Synthesis
tags: [technique, qwen3-tts, multilingual, language]
sources: [https://github.com/QwenLM/Qwen3-TTS, https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base]
created: 2026-04-16
updated: 2026-04-16
---

# Multilingual Speech Synthesis

## When to Use

- Generating speech in a language other than English
- Producing content where the input text may contain multiple languages
- Ensuring the model uses the correct phonology for a specific language when auto-detection might be ambiguous
- Building multilingual applications (e.g., localized audio content for 10+ markets)

## Technique

All Qwen3-TTS model variants support the same 10 languages. The `language` parameter tells the model which phonological and prosodic rules to apply when generating speech.

**Supported languages:**

| Language   | Language value to pass |
|------------|------------------------|
| Chinese    | `"Chinese"`            |
| English    | `"English"`            |
| Japanese   | `"Japanese"`           |
| Korean     | `"Korean"`             |
| German     | `"German"`             |
| French     | `"French"`             |
| Russian    | `"Russian"`            |
| Portuguese | `"Portuguese"`         |
| Spanish    | `"Spanish"`            |
| Italian    | `"Italian"`            |
| Auto-detect | `"Auto"` (default)   |

Language values are case-insensitive. Omitting the `language` parameter entirely defaults to `"Auto"`.

**Auto-detection** (`"Auto"`) works well for texts that are clearly in a single language. The model inspects the tokenized text and infers the dominant language before generation. It is the recommended default for most use cases.

**Explicit language selection** is preferred when:
- The text contains transliterated words or loanwords that could be ambiguous
- Mixed-script text might confuse auto-detection
- You need deterministic behavior regardless of text content
- The text is very short and lacks enough context for reliable detection

**Mixed-language handling:** The model can handle texts that mix two languages (e.g., a Chinese sentence with English brand names) when `language="Auto"`. For batches where each item is a different language, pass a list of language strings matching the list of texts.

## CLI Commands

Generate English speech (explicit):

```bash
python qwen3_tts_cli.py generate text "Good morning, how are you?" \
  --speaker Aiden \
  --language English \
  -o english_output.wav
```

Generate Chinese speech:

```bash
python qwen3_tts_cli.py generate text "你好，欢迎使用语音合成系统。" \
  --speaker Serena \
  --language Chinese \
  -o chinese_output.wav
```

Use auto-detection (default behavior):

```bash
python qwen3_tts_cli.py generate text "Bonjour, comment allez-vous?" \
  --speaker Ryan \
  -o french_output.wav
```

Batch generation with per-item language (conceptual — language list matches text list):

```bash
python qwen3_tts_cli.py generate text "Hello." "Hola." "Bonjour." \
  --language English Spanish French \
  --speaker Aiden \
  -o batch_output/
```

Generate Japanese with the Japanese speaker:

```bash
python qwen3_tts_cli.py generate text "おはようございます。今日もよろしくお願いします。" \
  --speaker Ono_Anna \
  --language Japanese \
  -o japanese_greeting.wav
```

## Under the Hood

The `language` parameter is validated against `get_supported_languages()` at wrapper level before any generation occurs. The validated language string(s) are passed as a `languages` list directly into `model.generate()`.

Inside the model, the language tag conditions the generation similarly to the speaker tag — it biases the transformer's output distribution toward the phonological patterns of the specified language. This is not a separate language model; the same transformer handles all 10 languages using a shared vocabulary trained on multilingual data.

Auto-detection happens in the preprocessing step when `language=None` or `language="Auto"`. The model inspects the character set and Unicode ranges in the text to infer the most likely language before constructing the generation context.

For batch inputs, each item in the text list can have its own language string — pass a list of equal length.

## Gotchas

- **Language selection affects pronunciation, not the speaker's vocal identity.** Asking `Aiden` (an English speaker) to speak Chinese will work, but the accent may be non-native.
- **Auto-detection can fail on very short texts** or texts with unusual character combinations. Use explicit language for one or two words.
- **Mixed-language texts are not perfectly handled.** If a Chinese sentence contains English words, the model may mispronounce the English portions or vice versa. For critical accuracy, consider splitting mixed-language sentences and generating each segment separately.
- **Language validation is case-insensitive**, but the list returned by `get_supported_languages()` is all-lowercase. When passing a list for batch generation, any capitalization is accepted.
- Passing an unsupported language string raises a `ValueError` listing valid options — fail fast before any GPU computation.
- Languages not in the supported list (e.g., Arabic, Hindi) will raise an error regardless of whether the text is valid Unicode.

## Sources

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base

## Learned from Usage

(No usage notes yet.)
