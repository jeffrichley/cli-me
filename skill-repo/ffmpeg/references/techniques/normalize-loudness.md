# Normalize Loudness

## When to Use

Use this technique whenever audio will be consumed by listeners across multiple devices or platforms. Inconsistent loudness is one of the most common complaints from podcast audiences, video viewers, and streaming listeners. Normalize when:

- Publishing a podcast episode (target: -16 LUFS)
- Uploading to YouTube or Spotify (target: -14 LUFS)
- Delivering broadcast content (target: -23 LUFS, EBU R128)
- Mixing multiple clips that were recorded at different gain levels
- Mastering a voice recording before adding music or effects

Single-pass normalization using simple peak or RMS methods produces inconsistent results because it doesn't account for perceived loudness across the full dynamic range. Two-pass loudnorm is the only reliable approach.

## Technique

The `loudnorm` filter implements the EBU R128 loudness standard. It measures integrated loudness (I), true peak (TP), and loudness range (LRA). Two passes are required:

**Pass 1 — Measure.** Run the filter in analysis mode (`print_format=json`) and capture the JSON output from stderr. This pass does not produce usable audio output; use `-f null -` to discard it.

**Pass 2 — Apply.** Feed the measured values back into the filter as `measured_I`, `measured_TP`, `measured_LRA`, `measured_thresh`, and `offset`. This allows the filter to make a single precise linear gain correction rather than the dynamic corrections it would make with no prior knowledge.

**Why single-pass fails.** Without measured values, `loudnorm` operates dynamically — it continuously adjusts gain as it processes the audio. This creates audible pumping artifacts and can upsample the signal to 192kHz internally if sample rates don't align. Always add `-ar 48000` on the output to lock the sample rate.

**Targets by platform:**

| Platform | Integrated | True Peak | LRA |
|---|---|---|---|
| Podcast | -16 LUFS | -1.5 dBTP | 11 LU |
| YouTube / Spotify | -14 LUFS | -1.0 dBTP | 11 LU |
| Broadcast (EBU R128) | -23 LUFS | -1.0 dBTP | 18 LU |
| Apple Podcasts | -16 LUFS | -1.0 dBTP | 11 LU |

## CLI Commands

**Pass 1 — Analysis only (discard output):**
```bash
ffmpeg -i input.wav \
  -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json \
  -f null - 2>&1 | tail -n 12
```

The JSON block appears at the end of stderr. It looks like:
```json
{
  "input_i": "-23.45",
  "input_tp": "-3.21",
  "input_lra": "7.80",
  "input_thresh": "-34.12",
  "input_loudness_range": "7.80",
  "output_i": "-16.00",
  "output_tp": "-1.55",
  "output_lra": "7.80",
  "output_thresh": "-26.67",
  "output_loudness_range": "7.80",
  "normalization_type": "Linear",
  "target_offset": "0.12"
}
```

**Pass 2 — Apply with measured values:**
```bash
ffmpeg -i input.wav \
  -af loudnorm=I=-16:TP=-1.5:LRA=11:\
measured_I=-23.45:measured_TP=-3.21:measured_LRA=7.80:\
measured_thresh=-34.12:offset=0.12:linear=true:print_format=summary \
  -ar 48000 output_normalized.wav
```

**YouTube / Spotify target (-14 LUFS):**
```bash
# Pass 1
ffmpeg -i input.wav \
  -af loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json \
  -f null - 2>&1 | tail -n 12

# Pass 2 (substitute measured values from above)
ffmpeg -i input.wav \
  -af loudnorm=I=-14:TP=-1.0:LRA=11:\
measured_I=<input_i>:measured_TP=<input_tp>:measured_LRA=<input_lra>:\
measured_thresh=<input_thresh>:offset=<target_offset>:linear=true \
  -ar 48000 output_youtube.wav
```

**Broadcast / EBU R128 (-23 LUFS):**
```bash
ffmpeg -i input.wav \
  -af loudnorm=I=-23:TP=-1.0:LRA=18:\
measured_I=<input_i>:measured_TP=<input_tp>:measured_LRA=<input_lra>:\
measured_thresh=<input_thresh>:offset=<target_offset>:linear=true \
  -ar 48000 output_broadcast.wav
```

**Full automation shell script (two-pass, configurable target):**
```bash
#!/usr/bin/env bash
# normalize.sh — two-pass EBU R128 loudness normalization
# Usage: normalize.sh input.wav [output.wav] [target_lufs]
# Defaults: output = input_normalized.wav, target = -16 LUFS (podcast)

set -euo pipefail

INPUT="${1:?Usage: normalize.sh input.wav [output.wav] [target_lufs]}"
OUTPUT="${2:-${INPUT%.*}_normalized.${INPUT##*.}}"
TARGET_I="${3:--16}"
TARGET_TP="-1.5"
TARGET_LRA="11"

echo "==> Pass 1: measuring loudness of '$INPUT'..."

# Capture stderr (where ffmpeg writes loudnorm JSON)
STATS=$(ffmpeg -hide_banner -i "$INPUT" \
  -af "loudnorm=I=${TARGET_I}:TP=${TARGET_TP}:LRA=${TARGET_LRA}:print_format=json" \
  -f null - 2>&1)

# Parse JSON values (requires jq)
JSON=$(echo "$STATS" | grep -A 12 '"input_i"' | head -13)

MEASURED_I=$(echo     "$JSON" | jq -r '.input_i')
MEASURED_TP=$(echo    "$JSON" | jq -r '.input_tp')
MEASURED_LRA=$(echo   "$JSON" | jq -r '.input_lra')
MEASURED_THRESH=$(echo "$JSON" | jq -r '.input_thresh')
OFFSET=$(echo         "$JSON" | jq -r '.target_offset')

echo "    Measured I:      $MEASURED_I LUFS"
echo "    Measured TP:     $MEASURED_TP dBTP"
echo "    Measured LRA:    $MEASURED_LRA LU"
echo "    Thresh:          $MEASURED_THRESH"
echo "    Offset:          $OFFSET"
echo ""
echo "==> Pass 2: applying normalization → '$OUTPUT'..."

ffmpeg -hide_banner -i "$INPUT" \
  -af "loudnorm=I=${TARGET_I}:TP=${TARGET_TP}:LRA=${TARGET_LRA}:\
measured_I=${MEASURED_I}:measured_TP=${MEASURED_TP}:measured_LRA=${MEASURED_LRA}:\
measured_thresh=${MEASURED_THRESH}:offset=${OFFSET}:linear=true:print_format=summary" \
  -ar 48000 \
  "$OUTPUT"

echo ""
echo "Done. Output: $OUTPUT"
```

Save as `normalize.sh`, make executable with `chmod +x normalize.sh`, then:
```bash
./normalize.sh episode.wav                          # podcast default (-16 LUFS)
./normalize.sh episode.wav episode_yt.wav -14       # YouTube
./normalize.sh episode.wav episode_bc.wav -23       # broadcast
```

## Under the Hood

The `loudnorm` filter implements ITU-R BS.1770-3 integrated loudness measurement. Integrated loudness (LUFS, Loudness Units relative to Full Scale) is a perceptual measurement that weights frequencies the way human hearing does — it is not the same as RMS or peak level.

During Pass 1, the filter scans the entire file and produces five statistics:

- `input_i` — integrated loudness of the source
- `input_tp` — true peak (intersample peak, more accurate than sample-level peak)
- `input_lra` — loudness range (difference between loud and quiet passages)
- `input_thresh` — the gating threshold used for measurement
- `target_offset` — the gain delta needed to hit the target

During Pass 2, when `linear=true` is set and all measured values are supplied, the filter applies a single fixed gain rather than dynamic correction. This is called linear normalization. The result is transparent — the dynamics of the original recording are preserved; only the overall level shifts.

Without measured values (single-pass mode), the filter uses dynamic normalization: it continuously adjusts gain as it encounters louder and quieter sections. This causes audible level pumping and is appropriate only for live streaming where a second pass is impossible.

The `-ar 48000` flag on the output prevents an ffmpeg quirk where `loudnorm` internally resamples to 192kHz under certain conditions (typically when the filter chain needs intermediate upsampling). Explicitly setting the output sample rate forces a clean final resample rather than leaving the internal state set to 192kHz.

## Sources

- k.ylo.ph: "FFmpeg Loudness Normalization" — the canonical reference for two-pass workflow and JSON parsing. https://k.ylo.ph/2016/04/04/loudnorm.html
- Peter Forgacs blog: "Audio Loudness Normalization with FFmpeg" — explains single-pass vs two-pass and when linear mode is appropriate. https://peterforgacs.github.io/2018/05/20/Audio-normalization-with-ffmpeg/
- ffmpeg-normalize (GitHub: slhck/ffmpeg-normalize) — Python CLI wrapper that automates two-pass; reviewing its source confirms the JSON field names and correct pass 2 filter string format. https://github.com/slhck/ffmpeg-normalize

## Learned from Usage

- The JSON from Pass 1 appears at the very end of stderr, after all the other ffmpeg progress output. Use `tail -n 12` or pipe to `jq` after stripping non-JSON lines with `grep -A 12 '"input_i"'`.
- If `normalization_type` in the Pass 1 JSON reads `"Dynamic"` instead of `"Linear"`, the filter fell back to dynamic mode — this happens when the measured offset would exceed the filter's gain range, OR when the audio has zero LRA (e.g., a pure tone or constant-level signal). Dynamic fallback still produces a valid output file; it is only a problem if artifact-free linear normalization is required. Consider using `volume` to pre-attenuate before normalizing when linear mode is needed.
- For MP3 output, set `-b:a 192k` or higher; loudnorm at -14 LUFS on a low-bitrate MP3 will reveal compression artifacts that were previously masked by louder playback.
- True peak limiting at -1.5 dBTP (not -1.0) gives extra headroom to survive lossy encoding, which can push intersample peaks above the measured true peak.
- When processing a folder of files, run Pass 1 on all files first, collect all JSON into a lookup table, then run all Pass 2 encodes — this avoids reading each source file twice in serial.
