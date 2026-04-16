---
title: Voice Design
tags: [technique, qwen3-tts, voice-design, instruct]
sources: [https://github.com/QwenLM/Qwen3-TTS, https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign]
created: 2026-04-16
updated: 2026-04-16
---

# Voice Design

## When to Use

- Creating a new voice persona purely from a text description, with no reference audio
- Generating a voice that matches specific character attributes (age, gender, accent, emotion)
- Rapid prototyping of voice options before committing to voice cloning
- Building synthetic voices for fictional characters without a real-world counterpart

## Technique

Voice design is only available on **`Qwen3-TTS-12Hz-1.7B-VoiceDesign`**. There is no 0.6B voice design model.

The `instruct` parameter accepts a free-form natural language description of the desired voice. The model interprets these descriptions and generates speech that attempts to match the described characteristics.

**Attributes the model understands:**

- **Gender**: "male", "female", "androgynous"
- **Age**: "child", "young adult", "middle-aged", "elderly"
- **Tone/Timbre**: "warm", "bright", "husky", "gravelly", "smooth", "nasal"
- **Emotion/Style**: "cheerful", "calm", "authoritative", "gentle", "energetic", "melancholic"
- **Accent**: English accents (American, British), named regional accents
- **Pacing**: "slow", "fast", "measured"
- **Delivery style**: "newsreader", "storyteller", "conversational", "dramatic"

**Writing effective descriptions:**

Combine multiple attributes into a single coherent sentence. The model responds better to natural prose than keyword lists. Be specific rather than vague.

Good: `"A warm, middle-aged British female voice with a calm and reassuring tone, speaking at a measured pace."`

Weaker: `"nice voice female british"`

An empty string for `instruct` is allowed — the model will pick a default style. This is similar to VoiceDesign with no direction, producing variable and potentially unpredictable results.

## CLI Commands

Design a voice from a description:

```bash
python qwen3_tts_cli.py design text "Welcome to the museum." \
  --description "A warm, authoritative male narrator voice, clear American accent, slow and measured delivery." \
  -o museum_intro.wav
```

Generate with an emotional style:

```bash
python qwen3_tts_cli.py design text "I can't believe what just happened!" \
  --description "An excited young female voice, energetic and slightly breathless." \
  -o reaction.wav
```

Generate a child character voice:

```bash
python qwen3_tts_cli.py design text "Can we go to the park today?" \
  --description "A playful young child's voice, curious and enthusiastic." \
  -o child.wav
```

## Under the Hood

The `generate_voice_design` method passes the `instruct` description as `instruct_ids` — tokenized instruction text prepended to the synthesis context as a user-turn prompt. The model attends to the instruction while generating codec tokens for the synthesis text.

This is the same mechanism as the `instruct` parameter in CustomVoice, but here the description shapes the entire voice identity rather than modifying an existing speaker's style.

Because generation is non-deterministic, the same description will produce slightly different voices across runs. If you need a reproducible voice, extract it with a consistent seed or use voice cloning after generating a satisfactory sample.

The VoiceDesign model is the 1.7B transformer; no 0.6B variant exists for this capability.

## Gotchas

- **VoiceDesign model only.** This method will raise an error if called on a Base or CustomVoice model.
- **Voice is not reproducible across runs** by default. Due to sampling, the same description generates a different voice each time. If consistency is needed, generate one sample you like, then use voice cloning from that sample.
- **Accent fidelity is limited.** The model can approximate accents but does not perfectly reproduce every regional accent. Test before committing to a description.
- **Emotional range is constrained.** Extreme emotions (rage, sobbing) may not render convincingly — the model tends toward moderate expressiveness.
- **Empty instruct string is valid but unpredictable.** Results vary widely without guidance.
- An overly long description does not necessarily improve results and can confuse the model. Aim for 1-2 concise sentences.

## Sources

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign

## Learned from Usage

(No usage notes yet.)
