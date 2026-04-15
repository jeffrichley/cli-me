# Denoise Audio

## When to Use

Use denoising when a recording has consistent or variable background noise that wasn't prevented at capture time. Choose the right filter based on the noise type:

- **afftdn** (FFT Denoiser) — best for stationary noise: HVAC, fans, air conditioning, computer hum, electrical hiss. The noise must be consistent in character and level throughout the file.
- **arnndn** (RNN Denoiser) — best for complex or varying noise: wind, room reverberation, traffic, crowd murmur, recording in a live space. Uses a neural network model trained on speech/noise pairs.

Do NOT apply heavy denoising to music recordings — it will strip harmonics and introduce metallic artifacts. Denoising is almost exclusively a voice/speech technique.

## Technique

### afftdn — FFT-based stationary noise reduction

`afftdn` uses Wiener filtering in the frequency domain. It estimates the noise floor by profiling a region of audio that contains noise but no speech, then suppresses frequencies that match that profile.

**Noise profiling workflow:**

1. Identify a moment of pure noise in the recording (the first 0.5 seconds before the speaker starts is common).
2. Use `asendcmd` to send a `start` command to `afftdn` at timestamp 0.0 and a `stop` command at 0.5. This tells the filter to learn the noise floor from that window.
3. After the profile window, `afftdn` applies the learned noise model to the rest of the file.

**Safe parameter ranges:**

- `nr` (noise reduction amount): 10–15 is transparent, 20+ causes metallic "underwater" artifacts
- `nf` (noise floor in dBFS): set to approximately your measured noise floor; -25 is a reasonable default for home studio recordings
- `om=o` — output only the original signal (without the noise reduction applied separately)

**afftdn with tracking** uses `tn=1` (tracking enabled) to continuously update the noise estimate as the recording progresses. This helps when noise changes slightly over time (e.g., HVAC cycling on and off) but can occasionally misidentify soft speech as noise during quiet passages.

### arnndn — Neural network RNN denoiser

`arnndn` applies a recurrent neural network trained to separate speech from noise. It works on complex, non-stationary noise that `afftdn` cannot profile.

**Model files** are required. The standard source is richardpl's repository on GitHub. Download `.rnnn` model files and reference them with the `model` parameter.

Common models:
- `std.rnnn` — general purpose, good starting point for most voice recordings
- `mp.rnnn` — slightly more aggressive, better for noisy outdoor recordings
- `cb.rnnn` — targeted at close-mic speech with room reflections

The `mix` parameter (0.0–1.0) controls how much of the denoised signal to blend with the original. `mix=1.0` is fully denoised. `mix=0.8` retains 20% of the original signal, which softens the processing artifacts while still reducing noise significantly. Start at `mix=0.8` and increase only if noise persists.

### Combining both filters

For heavily degraded recordings, chain `afftdn` first to remove stationary hiss, then `arnndn` to handle the remaining complex noise. The order matters — `afftdn` reduces the overall noise floor, which improves the signal-to-noise ratio that `arnndn`'s model works with.

## CLI Commands

**afftdn with noise profiling (profile first 0.5 seconds):**
```bash
ffmpeg -i input.wav \
  -af "asendcmd=0.0 afftdn sn start,asendcmd=0.5 afftdn sn stop,afftdn=nf=-25" \
  output_denoised.wav
```

**afftdn with manual noise reduction level:**
```bash
ffmpeg -i input.wav \
  -af "afftdn=nr=12:nf=-25" \
  output_denoised.wav
```

`nr=12` is a conservative setting. Increase to 15–18 for heavier reduction, but listen carefully for metallic artifacts. Stop before `nr=20`.

**afftdn with tracking enabled (for slowly varying noise):**
```bash
ffmpeg -i input.wav \
  -af "afftdn=nr=10:nf=-25:tn=1" \
  output_tracked.wav
```

**arnndn with model file:**
```bash
# Download model first:
# curl -L -o std.rnnn https://github.com/richardpl/arnndn-models/raw/master/std.rnnn

ffmpeg -i input.wav \
  -af "arnndn=model=/path/to/std.rnnn:mix=0.8" \
  output_rnn.wav
```

**arnndn for video with audio track (preserve video stream):**
```bash
ffmpeg -i input.mp4 \
  -vf copy \
  -af "arnndn=model=/path/to/std.rnnn:mix=0.8" \
  -c:v copy \
  output_denoised.mp4
```

`-c:v copy` passes the video stream through without re-encoding.

**Combined chain — afftdn then arnndn for heavily degraded audio:**
```bash
ffmpeg -i input.wav \
  -af "asendcmd=0.0 afftdn sn start,asendcmd=0.5 afftdn sn stop,\
afftdn=nf=-25:nr=12,\
arnndn=model=/path/to/std.rnnn:mix=0.85" \
  output_heavy_denoise.wav
```

**Full voice processing chain (denoise + normalize):**
```bash
ffmpeg -i input.wav \
  -af "asendcmd=0.0 afftdn sn start,asendcmd=0.5 afftdn sn stop,\
afftdn=nf=-25:nr=12,\
arnndn=model=/path/to/std.rnnn:mix=0.8,\
loudnorm=I=-16:TP=-1.5:LRA=11" \
  output_voice_clean.wav
```

Note: for best loudnorm results, follow the two-pass process described in normalize-loudness.md. The single-pass loudnorm shown here is acceptable for quick previews.

## Under the Hood

### How afftdn works

`afftdn` transforms the audio signal into the frequency domain using a short-time FFT. For each frequency bin, it estimates the power spectral density of the noise versus the signal, then applies a Wiener filter gain to suppress bins that are dominated by noise.

The noise profile (learned during the `sn start/stop` window) stores the expected noise power at each frequency bin. During playback, any bin whose energy closely matches the stored profile is attenuated. Bins with significantly more energy than the profile (indicating speech) are left relatively untouched.

The `nr` parameter scales the aggressiveness of the Wiener filter. At low values (10–12), only bins that clearly match the noise profile are attenuated. At high values (>20), the filter begins suppressing bins that partially overlap with the noise profile — including harmonics of speech, which causes the characteristic metallic "underwater" artifact.

The `nf` parameter sets the noise floor in dBFS. This is a secondary threshold: bins below `nf` are treated as noise regardless of the profile. Set this to approximately the measured RMS level of a silent region using `volumedetect`.

### How arnndn works

`arnndn` uses a recurrent neural network (GRU architecture) that was trained offline on large speech + noise datasets. The model learns to classify short-time spectral features as either speech or noise and outputs a suppression mask for each frequency band.

Because the model is trained on real-world noise/speech pairs rather than derived from a mathematical noise model, it generalizes well to complex and varying noise types that `afftdn` cannot profile. The tradeoff is that it cannot be tuned per-recording the way `afftdn` can — you choose a model and a mix ratio, and those are your controls.

The `mix` parameter blends the denoised output with the input: `mix=1.0` gives the fully denoised signal, `mix=0.0` gives the original unchanged. Values between 0.7 and 0.9 are typically best for voice recordings — they reduce noise perception while avoiding the slightly "processed" quality of full denoising.

Model files are architecture-specific to the `arnndn` filter's implementation. Models from other noise reduction systems are not compatible.

## Sources

- FFmpeg filter documentation for `afftdn`: https://ffmpeg.org/ffmpeg-filters.html#afftdn
- FFmpeg filter documentation for `arnndn`: https://ffmpeg.org/ffmpeg-filters.html#arnndn
- ffmpegbyexample — practical examples for afftdn profiling workflow: https://ffmpegbyexample.com
- richardpl/arnndn-models GitHub repository (model files): https://github.com/richardpl/arnndn-models

## Learned from Usage

- The `asendcmd` syntax is sensitive to spacing. The exact form is `asendcmd=TIMESTAMP FILTERNAME COMMAND VALUE` — extra spaces around the equals sign or missing spaces between tokens will silently fail with no error, leaving `afftdn` without a noise profile.
- If there is no clean noise region at the start of the file (speaker starts talking immediately), add 0.5 seconds of silence at the head with `apad=pad_len=24000` (at 48kHz), profile that, then trim the padding with `atrim=start=0.5` afterward.
- `nr=15` is the practical maximum before artifacts become noticeable on close-mic voice. If `nr=15` isn't enough, switch to `arnndn` rather than pushing `nr` higher.
- `arnndn` with `mix=0.8` on a recording that was already clean can introduce a slight "telephone" quality — if the input is already acceptable, skip the RNN step and use `afftdn` at `nr=10` only.
- When chaining both filters on a video file, apply them in a single `-af` string rather than two separate `-af` flags — ffmpeg only honors the last `-af` flag if you specify multiple.
- The `std.rnnn` model from the richardpl repository is the safest general-purpose choice. The `mp.rnnn` model is more aggressive and occasionally suppresses sibilants (s, sh, f sounds) in female voices.
