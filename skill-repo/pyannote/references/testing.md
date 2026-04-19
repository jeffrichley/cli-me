# Testing the pyannote skill

Tier 1 (`test_commands.py`) and Tier 2 (`test_integration.py` `*Integration`
classes) always run with an HF token, but they exercise the pipeline against a
sine-tone fixture. Speech models return empty results on tones, so most Tier 2
assertions only check shape and non-crashing — not substance. This is the
**synthetic fixture trap**: tests "pass" because there's nothing to assert on.

## Tier 3 — real-speech assertions

`*RealSpeech` classes in `test_integration.py` run only when two real-speech
fixtures exist (not committed; see `.gitignore`):

- `single_speaker.wav` — ~9s, 16kHz mono. Built from SpeechBrain's
  `tests/samples/ASR/spk1_snt1.wav` (Apache 2.0) concatenated 3× with silences.
- `two_speakers.wav` — pyannote-audio's `tutorials/assets/sample.wav` (MIT),
  ~30s multi-speaker conversation; pyannote's own canonical diarization demo.

Generate them:

```
python qa/pyannote/fixtures/fetch_speech_fixtures.py
```

SHA-256 hashes are baked into the script and verified post-download. Idempotent.

Tests unlocked:

- `TestVadRealSpeech` — ≥1 speech region; speech > 50% of clip.
- `TestDiarizeRealSpeech` — ≥2 distinct speaker labels.
- `TestEmbedRealSpeech` — self-sim > 0.9; cross-speaker sim ≥ 0.1 below self-sim.
- `TestVerifyRealSpeech` — matched clips `same_speaker=True`; cross-speaker `False`.
