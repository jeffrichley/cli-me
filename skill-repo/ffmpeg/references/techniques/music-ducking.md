# Music Ducking

## When to Use

Use music ducking when you need background music to lower in volume automatically whenever a voice is present, then return to normal volume during pauses. Common use cases:

- Podcast intro/outro music that fades under the host's voice
- Video narration with background score
- Interview recordings with ambient music bed
- YouTube videos where music should be audible between spoken segments but not compete with speech

There are two approaches:

- **Static mix** — set the music to a fixed lower volume and mix it with the voice at constant levels. Simple, no automation, works well when music and voice are always playing at the same time.
- **Dynamic ducking (sidechaincompress)** — the voice track controls a compressor on the music track. When voice is present, the music is automatically attenuated. When voice stops, the music returns to full volume. This sounds more professional and requires no manual keyframing.

## Technique

### Static mix

Use `volume` to attenuate the music, then use `amix` to combine the two streams. The critical detail with `amix` is the `normalize` parameter.

**`normalize=0` is mandatory.** By default (`normalize=1`), `amix` divides every input by the number of inputs — so two inputs each get multiplied by 0.5. This means your carefully set voice and music levels are both halved. Setting `normalize=0` disables this behavior and passes each stream at its set level.

Use `weights` to control the relative blend without needing a separate `volume` filter: `weights=1 0.15` means input 1 (voice) at 100% and input 2 (music) at 15%.

### Dynamic ducking with sidechaincompress

`sidechaincompress` is a compressor that takes two audio inputs: the signal to compress (music) and the sidechain signal that controls the compression (voice). When the sidechain signal exceeds the threshold, the compressor attenuates the primary signal.

Key parameters:

- `threshold=0.02` — the linear amplitude level at which ducking starts. 0.02 is approximately -34 dBFS, which triggers on normal conversational voice.
- `ratio=8` — how aggressively the music is reduced. 8:1 means for every 8 dB the sidechain exceeds the threshold, the music output rises only 1 dB. High ratios produce more obvious ducking.
- `attack=100` — time in milliseconds for the compressor to reach full attenuation after voice begins. 100ms prevents sudden level drops on word onsets.
- `release=700` — time in milliseconds for the music to return to full level after voice stops. 700ms gives a natural fade-up. Shorter values sound jarring.
- `knee=6` — soft-knee width in dB. Softens the transition into compression so ducking sounds gradual rather than snapping on.
- `level_sc=0.9` — scale the sidechain signal before it hits the detector. Useful for fine-tuning the sensitivity.

The routing for dynamic ducking requires `asplit` to split the voice into two paths: one goes to the final output, the other becomes the sidechain control signal that feeds `sidechaincompress`.

## CLI Commands

**Static mix — music at 15% with voice:**
```bash
ffmpeg -i voice.wav -i music.wav \
  -filter_complex "\
[1:a]volume=0.15[music_quiet];\
[0:a][music_quiet]amix=inputs=2:normalize=0[out]" \
  -map "[out]" output_static.wav
```

**Static mix using weights (no separate volume filter):**
```bash
ffmpeg -i voice.wav -i music.wav \
  -filter_complex "[0:a][1:a]amix=inputs=2:normalize=0:weights=1 0.15[out]" \
  -map "[out]" output_weights.wav
```

`weights=1 0.15` applies 1.0x gain to voice (input 0) and 0.15x gain to music (input 1). This is equivalent to the separate `volume=0.15` approach but more concise.

**Dynamic ducking — sidechaincompress (standard podcast settings):**
```bash
ffmpeg -i voice.wav -i music.wav \
  -filter_complex "\
[0:a]asplit=2[voice_out][voice_sc];\
[1:a][voice_sc]sidechaincompress=threshold=0.02:ratio=8:attack=100:release=700:knee=6[music_ducked];\
[voice_out][music_ducked]amix=inputs=2:normalize=0[out]" \
  -map "[out]" output_ducked.wav
```

Step by step:
1. `asplit=2` — split the voice into `[voice_out]` (goes to final mix) and `[voice_sc]` (sidechain signal)
2. `sidechaincompress` takes music as the primary signal and the voice sidechain as the trigger
3. `amix` combines the original voice with the ducked music at equal weights

**Aggressive ducking — music nearly disappears under voice:**
```bash
ffmpeg -i voice.wav -i music.wav \
  -filter_complex "\
[1:a]volume=0.4[music_pre];\
[0:a]asplit=2[voice_out][sidechain];\
[music_pre][sidechain]sidechaincompress=threshold=0.015:ratio=20:attack=50:release=1000:knee=2[ducked_music];\
[voice_out][ducked_music]amix=inputs=2:normalize=0[out]" \
  -map "[out]" output_aggressive.wav
```

This version adds a volume floor (`volume=0.08`) to the music so it never goes completely silent — even at maximum compression, you hear a faint bed.

**Weights-only approach for quick level balance (no sidechain):**
```bash
ffmpeg -i voice.wav -i music.wav \
  -filter_complex "\
[0:a]volume=1.0[v];\
[1:a]volume=0.12[m];\
[v][m]amix=inputs=2:normalize=0:duration=longest[out]" \
  -map "[out]" output_simple.wav
```

`duration=longest` keeps the mix running until the longest input ends, rather than stopping when the shortest input ends.

**Full production chain — denoise voice, duck music, normalize output:**
```bash
ffmpeg -i voice.wav -i music.wav \
  -filter_complex "\
[0:a]asendcmd=0.0 afftdn sn start,asendcmd=0.5 afftdn sn stop,afftdn=nf=-25:nr=12[voice_clean];\
[voice_clean]asplit=2[voice_out][voice_sc];\
[1:a]volume=0.2[music_pre];\
[music_pre][voice_sc]sidechaincompress=threshold=0.02:ratio=8:attack=100:release=700:knee=6[music_ducked];\
[voice_out][music_ducked]amix=inputs=2:normalize=0:duration=longest[mix];\
[mix]loudnorm=I=-16:TP=-1.5:LRA=11[out]" \
  -map "[out]" -ar 48000 output_final.wav
```

Note: the `loudnorm` step here is single-pass. For broadcast-quality output, run the two-pass process from normalize-loudness.md on the output file.

## Under the Hood

### amix and normalize

`amix` sums N audio streams. The `normalize` parameter controls whether the output is divided by N to maintain a consistent average level. With `normalize=1` (default), two equal-level inputs produce output at half the level of each. With `normalize=0`, the inputs are summed directly — two identical inputs at -20 dBFS produce -14 dBFS output (3 dB gain from summing coherent signals).

In music ducking scenarios, voice and music are not the same signal, so direct summing won't cause the same 3 dB coherent gain, but loud simultaneous passages can still clip. Set voice and music levels before `amix` (not after) so you can control headroom.

The `weights` parameter scales each input before mixing, equivalent to a `volume` filter on each input. `weights=1 0.15` on a two-input `amix` means `[input0 * 1.0 + input1 * 0.15]` as the summed output.

### sidechaincompress signal flow

`sidechaincompress` is a compressor with an external level detector. In a normal compressor, the level detector measures the signal being compressed. In sidechain compression, the level detector measures a separate signal — in this case, the voice.

When the voice sidechain exceeds the `threshold`, the compressor calculates a gain reduction for the music signal based on `ratio`. The `attack` and `release` times determine how quickly the gain reduction is applied and removed.

The `threshold=0.02` value is a linear amplitude ratio (0.0–1.0 scale), not decibels. Converting: `20 * log10(0.02) ≈ -34 dBFS`. This is a suitable threshold for typical voice recordings. If the voice is quiet and ducking isn't triggering, lower the threshold to `0.01` (-40 dBFS). If room noise is causing constant ducking even in silence, raise it to `0.03` (-30 dBFS).

`ratio=8` means: above the threshold, for every 8 dB the sidechain exceeds the threshold, the compressor output only rises 1 dB. For music ducking purposes, ratios of 5–10 work well. Ratios above 15 are effectively limiting — the music snaps to a floor level whenever voice is present.

`attack=100ms` is intentionally slow enough to not cut the first syllable of a word. `release=700ms` is slow enough to not pump between words in a sentence, but fast enough to bring the music back during a paragraph break.

## Sources

- FFmpeg filter documentation for `sidechaincompress`: https://ffmpeg.org/ffmpeg-filters.html#sidechaincompress
- FFmpeg filter documentation for `amix`: https://ffmpeg.org/ffmpeg-filters.html#amix
- GitHub Gist by mhavo — ducking with sidechaincompress, original reference for threshold/ratio/attack/release starting values: https://gist.github.com/mhavo

## Learned from Usage

- Forgetting `normalize=0` on `amix` is the most common mistake. The symptom is that the voice sounds quieter than expected after mixing — because `amix` silently divided it by the number of inputs. Always check the `amix` line first when levels seem wrong.
- The `asplit` for the sidechain must split the voice, not the music. Splitting the music to feed back into its own sidechain creates a compressor that triggers on itself — it will clamp the music regardless of whether voice is present.
- For intro/outro music where you want the music to play at full level before the voice starts, `sidechaincompress` handles this automatically — no signal on the sidechain means no compression, so the music plays at full level until the first word.
- `release=700` can feel slow on short sentences with quick pauses. Use `release=400` for conversational podcasts; use `release=700` or higher for narration with intentional dramatic pauses.
- When the voice recording has significant noise floor (room tone), the sidechain may trigger constantly because the noise floor exceeds `threshold=0.02`. Either denoise the voice before splitting (as in the full chain example), or raise the threshold to `0.05` to ignore the noise floor.
- To preview ducking behavior without rendering, pipe through ffplay: `ffmpeg -i voice.wav -i music.wav -filter_complex "[same chain]" -map "[out]" -f wav - | ffplay -`.
