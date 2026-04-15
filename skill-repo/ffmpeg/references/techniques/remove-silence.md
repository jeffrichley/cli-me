# Remove Silence

## When to Use

Use silence removal when raw recordings contain dead air that wasn't caught during editing, or when automating the cleanup of unattended recordings. Common situations:

- Trimming the head and tail of a podcast recording (mic left on before/after the session)
- Removing pauses between answers in an interview compilation
- Cleaning up screen recordings where the presenter stopped talking mid-capture
- Processing a batch of voice memos where every file has variable dead air at the start

Do NOT apply aggressive silence removal to music — it will strip intentional rests and breath marks. For music, use a much lower threshold and longer minimum duration, or skip this technique entirely.

## Technique

The `silenceremove` filter detects audio segments below a threshold and either removes them or leaves them alone. The key parameters are:

- `start_periods` — how many silence periods to skip at the start (1 = trim leading silence)
- `start_duration` — how long a silence must be before trimming begins (seconds)
- `start_threshold` — the dB level below which audio is considered silence
- `stop_periods` — how many silence periods to allow in the middle (-1 = remove all)
- `stop_duration` — minimum silence duration to remove from the middle
- `stop_threshold` — dB level for stop detection

**Finding the noise floor first.** Always run `volumedetect` on the source before choosing a threshold. The reported `mean_volume` is your noise floor reference. Set threshold 5-10 dB above the mean to catch hiss and room tone without cutting into speech.

```bash
ffmpeg -i input.wav -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

Typical thresholds:
- Quiet studio: -50 to -45 dB
- Home studio with background noise: -40 to -35 dB
- Laptop mic or noisy room: -35 to -30 dB

**The reverse trick.** The `silenceremove` filter is reliable for detecting silence at the start of a file (`start_periods=1`) but can fail to accurately trim silence at the tail. The standard workaround is the reverse trick: process the file in the forward direction to trim the head, then reverse the audio, trim what is now the new head (which was the original tail), then reverse again. This ensures both ends are trimmed with the same consistent logic.

**Adding padding.** A hard cut right at the first sample of speech sounds unnatural. Use `start_silence=0.3` to leave 300ms of audio before the silence threshold is crossed — this retains any breath or room tone immediately before speech begins.

## CLI Commands

**Trim leading and trailing silence only (no gap removal):**
```bash
ffmpeg -i input.wav \
  -af "silenceremove=start_periods=1:start_duration=0.3:start_threshold=-40dB:\
stop_periods=1:stop_duration=0.5:stop_threshold=-40dB" \
  output_trimmed.wav
```

**Remove all internal silence gaps (podcast cleanup):**
```bash
ffmpeg -i input.wav \
  -af "silenceremove=stop_periods=-1:stop_duration=1.0:stop_threshold=-35dB" \
  output_no_gaps.wav
```

`stop_periods=-1` means "remove every silence period found, not just the first one." `stop_duration=1.0` means gaps shorter than 1 second are kept — this preserves natural dramatic pauses while removing dead air.

**Reverse trick — reliable head and tail trimming:**
```bash
# Step 1: trim leading silence (forward)
ffmpeg -i input.wav \
  -af "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-40dB" \
  /tmp/step1.wav

# Step 2: reverse
ffmpeg -i /tmp/step1.wav -af areverse /tmp/step2.wav

# Step 3: trim leading silence of the reversed file (= trimming original tail)
ffmpeg -i /tmp/step2.wav \
  -af "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-40dB" \
  /tmp/step3.wav

# Step 4: reverse back to original orientation
ffmpeg -i /tmp/step3.wav -af areverse output_clean.wav
```

As a single filter chain (more efficient, one pass):
```bash
ffmpeg -i input.wav \
  -af "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-40dB,\
areverse,\
silenceremove=start_periods=1:start_duration=0.1:start_threshold=-40dB,\
areverse" \
  output_clean.wav
```

**Full chain with denoise before silence detection:**
```bash
ffmpeg -i input.wav \
  -af "afftdn=nr=12:nf=-25,\
silenceremove=start_periods=1:start_duration=0.3:start_threshold=-40dB,\
areverse,\
silenceremove=start_periods=1:start_duration=0.1:start_threshold=-40dB,\
areverse,\
silenceremove=stop_periods=-1:stop_duration=1.0:stop_threshold=-40dB" \
  output_final.wav
```

Denoise first so that background noise doesn't fool the silence detector into thinking there's always speech present.

**Quick volumedetect to find noise floor:**
```bash
ffmpeg -i input.wav -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume|RMS"
```

## Under the Hood

`silenceremove` works by comparing the short-term RMS energy of the audio signal against the threshold. When the signal drops below the threshold for at least `start_duration` or `stop_duration` seconds, that segment is flagged as silence and either skipped or cut.

The asymmetry between `start_periods` and `stop_periods` matters:

- `start_periods=1` — find the first silence block at the head and trim everything up to when audio begins
- `stop_periods=-1` — find every silence block anywhere in the file and remove each one
- `stop_periods=1` — trim only the first silence encountered after speech begins (useful for trimming the tail without touching the middle)

The filter does not add crossfades at the cut points. If you're removing middle-of-file gaps and the result sounds choppy, pipe the output through `aresample=async=1` or manually add fade-out/fade-in around each cut using `afade`.

The `areverse` filter reads the entire audio stream into memory before outputting it. For very long files (multi-hour recordings), this can consume significant RAM. On a 2-hour 48kHz stereo WAV at 32-bit float, that is approximately 1.5 GB. Use intermediate files (as shown in the step-by-step version) rather than the single filter chain if memory is a concern.

The threshold is always specified as a dB value relative to full scale. `-40dB` means signals more than 40 dB below 0 dBFS are considered silence. Threshold values are negative by convention; some older documentation shows positive numbers (e.g., `0.0001`) which is the linear amplitude ratio equivalent.

## Sources

- FFmpeg filter documentation for `silenceremove`: https://ffmpeg.org/ffmpeg-filters.html#silenceremove
- Transloadit demo and explanation of silenceremove parameters: https://transloadit.com/demos/audio-encoding/remove-silence-from-audio/
- FFmpeg wiki on audio filtering: https://trac.ffmpeg.org/wiki/AudioChannelManipulation

## Learned from Usage

- The single-chain reverse trick (four filters in one `-af` string) is cleaner for scripting but the intermediate-file version is easier to debug — run each step and check the output before proceeding.
- `start_silence=0.3` (the padding before the first speech) is not the same as `start_duration` (the minimum silence length). The naming is confusing. `start_duration` controls how long a silence must be to trigger trimming; `start_silence` controls how much silence to leave before the speech onset.
- When removing middle gaps, `stop_duration=0.5` is too aggressive for conversational recordings — it cuts out breaths between sentences. Use `1.0` as a starting point for podcasts and adjust downward only if needed.
- After silence removal, re-check loudness with `volumedetect` — the filter can create level spikes at edit points if the source had rapid fade-ins on loud material.
- On Windows, the reverse trick using intermediate temp files is more reliable than the single filter chain because Windows file locking sometimes causes issues with in-memory filter graphs that use `areverse` at high sample rates.
