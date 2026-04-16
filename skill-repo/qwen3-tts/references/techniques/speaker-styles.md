---
title: Speaker Styles and Instruct Parameter
tags: [technique, qwen3-tts, speakers, instruct, custom-voice]
sources: [https://github.com/QwenLM/Qwen3-TTS, https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice]
created: 2026-04-16
updated: 2026-04-16
---

# Speaker Styles and Instruct Parameter

## When to Use

- Selecting a specific built-in voice identity for your audio
- Modifying how a speaker delivers text (e.g., whispering, excited, slow) without changing their identity
- Building consistent multi-character dialogue where each character has a distinct voice

## Technique

The `speaker` parameter is only available on **CustomVoice model variants**:
- `Qwen3-TTS-12Hz-1.7B-CustomVoice` — supports all 9 speakers + `instruct`
- `Qwen3-TTS-12Hz-0.6B-CustomVoice` — supports all 9 speakers; `instruct` is silently ignored

Speaker names are validated case-insensitively. Pass any capitalization; the wrapper normalizes it.

The `instruct` parameter is a natural-language string that modifies the speaking style of the chosen speaker without changing their vocal identity. Think of it as directing an actor rather than casting a different one.

**The 9 built-in speakers:**

| Speaker    | Native Language         | Voice Character                                      |
|------------|-------------------------|------------------------------------------------------|
| Vivian     | Chinese                 | Bright, slightly edgy young female voice             |
| Serena     | Chinese                 | Warm, gentle young female voice                      |
| Uncle_Fu   | Chinese                 | Seasoned male voice with a low, mellow timbre        |
| Dylan      | Chinese (Beijing)       | Youthful Beijing male voice, clear and natural       |
| Eric       | Chinese (Sichuan)       | Lively Chengdu male voice, slightly husky brightness |
| Ryan       | English                 | Dynamic male voice with strong rhythmic drive        |
| Aiden      | English                 | Sunny American male voice with a clear midrange      |
| Ono_Anna   | Japanese                | Playful Japanese female voice, light and nimble      |
| Sohee      | Korean                  | Warm Korean female voice with rich emotion           |

**Effective instruct examples:**
- `"Speak slowly and clearly, as if presenting to a large audience."`
- `"Whisper this as if sharing a secret."`
- `"Read this with excitement and enthusiasm."`
- `"Deliver this in a calm, reassuring tone."`
- `"Speak with a sense of urgency."`

## CLI Commands

Generate with a specific speaker (no instruct):

```bash
python qwen3_tts_cli.py generate text "Good morning, everyone!" --speaker Aiden -o morning.wav
```

Generate with speaker + style instruction:

```bash
python qwen3_tts_cli.py generate text "Please hold while I connect your call." \
  --speaker Serena \
  --instruct "Speak in a professional, calm customer service tone." \
  -o hold_message.wav
```

List all available speakers with details:

```bash
python qwen3_tts_cli.py info speakers --pretty
```

Generate with the 0.6B model (instruct is ignored):

```bash
python qwen3_tts_cli.py generate text "Hello there." \
  --speaker Ryan \
  --model Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice \
  -o hello.wav
```

## Under the Hood

The speaker name is passed as a `speakers` list to `model.generate()`. Inside the model, the speaker identity is encoded as a learned embedding that conditions the transformer's attention, biasing generation toward the target speaker's codec patterns.

The `instruct` text is tokenized separately and provided as `instruct_ids`, forming a user-turn message before the synthesis assistant turn:

```
<|im_start|>user
{instruct}<|im_end|>
<|im_start|>assistant
{text}<|im_end|>
<|im_start|>assistant
```

This means the model sees the instruction as a directive from a user before producing the speech. The 0.6B model does not have the capacity to act on instruct tokens — the wrapper detects the 0.6B size and sets `instruct=None` silently.

Speaker names are listed in the model's config and returned by `get_supported_speakers()`. Passing an unsupported name raises a `ValueError` at validation time before any GPU computation occurs.

## Gotchas

- **CustomVoice model only.** The `speaker` parameter does not exist on Base or VoiceDesign models.
- **`instruct` is silently ignored on 0.6B models.** No error is raised — the instruction is simply discarded. Always use the 1.7B CustomVoice model if instruct guidance is needed.
- **Speaker names with underscores must be exact.** `Uncle_Fu` and `Ono_Anna` include underscores — missing or replacing them with spaces will fail validation.
- **All speakers can speak all 10 supported languages**, regardless of their "native language" listed above. The native language is their strongest/most natural language, not a restriction.
- **Instruct does not transform voice identity** — it modifies delivery style. You cannot instruct Aiden to sound like Serena.
- Overly complex or contradictory instructions may produce unpredictable style results.

## Sources

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice

## Learned from Usage

(No usage notes yet.)
