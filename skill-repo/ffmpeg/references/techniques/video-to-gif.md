# Video to GIF

## When to Use

Use this technique when converting a video clip to an animated GIF — for documentation, tutorials, social media posts, or anywhere a looping animation is needed without video player support. The primary concern is file size versus visual quality: GIF is limited to 256 colors per frame, so a naive conversion looks terrible. The two-pass palette approach is mandatory for acceptable quality.

Use the two-pass approach for anything that will be seen by another person. Use the single-pass only as a quick preview to check timing — never for final output.

Scale to 480px wide or less. Target 10–15 fps (CLI defaults to 15 for smoothness; use 10-12 for smaller files). GIF files above ~5 MB are impractical for web use; if you cannot get there by reducing size and fps, consider WebP or a short MP4 loop instead.

## Technique

### Why the Two-Pass Palette Approach is Mandatory

GIF supports exactly 256 colors per frame. FFmpeg's default single-pass approach maps every frame to a fixed generic 256-color palette — web-safe colors or a generic RGB spread. This produces visible banding, color shifts, and washed-out gradients on almost any real video content.

The two-pass approach generates a custom palette optimized specifically for the colors in your source video:

**Pass 1 — `palettegen`:** FFmpeg analyzes every frame of the (already scaled and fps-filtered) source and computes the optimal 256-color palette that best represents the color distribution of the actual content. This palette is saved as a small PNG file.

**Pass 2 — `paletteuse`:** FFmpeg encodes the GIF, mapping each pixel to the closest color in the custom palette and applying dithering to simulate intermediate colors. The result is dramatically better than the fixed-palette single-pass approach.

The quality difference is not subtle — single-pass output at the same file size looks like a low-quality JPEG artifact pattern, while two-pass output preserves smooth gradients and accurate colors.

### Dithering Options

Dithering simulates colors not in the palette by mixing adjacent pixels. The choice affects visual quality and file size:

| Algorithm | Size | Quality | Best For |
|-----------|------|---------|----------|
| `bayer:bayer_scale=2` | Smallest | Crosshatch pattern visible | Archival, compression priority |
| `floyd_steinberg` | Larger | Smooth, natural gradients | Photographic content |
| `sierra2_4a` | Medium | Balanced, default | General use |
| `none` | Smallest | Visible banding | Flat cartoon/illustration only |

### stats_mode for Static Backgrounds

`palettegen=stats_mode=diff` tells the palette generator to prioritize colors that appear in areas of motion (frame differences) rather than weighting all pixels equally. For videos with a mostly static background, this dramatically improves the rendering of the moving subject — the background eats fewer palette slots, leaving more for the action.

### Clip Extraction First

If you only want a portion of the video, trim it with ffmpeg to a separate file first (using `-c copy` for speed), then convert to GIF. This is faster than trimming and converting in a single pipeline, and lets you preview the trim before waiting for a full palette generation.

## CLI Commands

**Pass 1 — generate palette:**
```bash
ffmpeg -i input.mp4 \
  -vf "fps=12,scale=480:-1:flags=lanczos,palettegen" \
  palette.png
```

**Pass 2 — encode GIF using generated palette:**
```bash
ffmpeg -i input.mp4 -i palette.png \
  -lavfi "fps=12,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse" \
  output.gif
```

**Shell script combining both passes:**
```bash
#!/bin/bash
INPUT="$1"
OUTPUT="${INPUT%.*}.gif"
PALETTE=$(mktemp /tmp/palette_XXXXXX.png)

echo "Pass 1: generating palette..."
ffmpeg -v warning -i "$INPUT" \
  -vf "fps=12,scale=480:-1:flags=lanczos,palettegen" \
  "$PALETTE"

echo "Pass 2: encoding GIF..."
ffmpeg -v warning -i "$INPUT" -i "$PALETTE" \
  -lavfi "fps=12,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse" \
  "$OUTPUT"

rm "$PALETTE"
echo "Done: $OUTPUT"
```

**With explicit dithering options (floyd_steinberg — best for photos):**
```bash
# Pass 1
ffmpeg -i input.mp4 \
  -vf "fps=12,scale=480:-1:flags=lanczos,palettegen=stats_mode=diff" \
  palette.png

# Pass 2
ffmpeg -i input.mp4 -i palette.png \
  -lavfi "fps=12,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=floyd_steinberg" \
  output.gif
```

**With bayer dithering (smallest file, crosshatch pattern):**
```bash
# Pass 1
ffmpeg -i input.mp4 \
  -vf "fps=10,scale=320:-1:flags=lanczos,palettegen" \
  palette.png

# Pass 2
ffmpeg -i input.mp4 -i palette.png \
  -lavfi "fps=10,scale=320:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=2" \
  output.gif
```

**Clip extraction before conversion (trim first, then convert):**
```bash
# Step 1: extract clip (fast, no re-encode)
ffmpeg -ss 00:00:05 -to 00:00:12 -i input.mp4 -c copy clip.mp4

# Step 2: pass 1 on the clip
ffmpeg -i clip.mp4 \
  -vf "fps=12,scale=480:-1:flags=lanczos,palettegen=stats_mode=diff" \
  palette.png

# Step 3: pass 2
ffmpeg -i clip.mp4 -i palette.png \
  -lavfi "fps=12,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse" \
  output.gif
```

**Small web-optimized GIF (320px, 10fps, aggressive compression):**
```bash
# Pass 1
ffmpeg -i input.mp4 \
  -vf "fps=10,scale=320:-1:flags=lanczos,palettegen=max_colors=128:stats_mode=diff" \
  palette.png

# Pass 2
ffmpeg -i input.mp4 -i palette.png \
  -lavfi "fps=10,scale=320:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
  output.gif
```

**Single-pass (quick preview ONLY — do not use for final output):**
```bash
ffmpeg -i input.mp4 -vf "fps=12,scale=480:-1:flags=lanczos" output_preview.gif
```

## Under the Hood

GIF uses the LZW compression algorithm on indexed color data. Each pixel is stored as an index into a palette of up to 256 colors. LZW compression is effective on runs of identical palette indices — meaning large flat-color areas compress well, while dithered areas (which alternate pixel colors to simulate gradients) compress poorly. This is the core tension: dithering improves visual quality but increases file size.

The `palettegen` filter performs a median cut algorithm over the pixels of all analyzed frames to find the 256 colors that minimize total quantization error. When `stats_mode=diff` is set, it weights pixel samples by their temporal difference from the previous frame — effectively giving more palette slots to the colors that appear in moving areas.

The `paletteuse` filter takes the palette PNG as a second input and, for each frame, maps every pixel to its nearest palette entry (by Euclidean distance in RGB space), then applies the selected dithering algorithm to distribute quantization error across neighboring pixels. Floyd-Steinberg error diffusion propagates error forward and downward, producing organic-looking gradients. Bayer ordered dithering uses a fixed threshold matrix, producing a geometric crosshatch pattern that is more compressible (better LZW runs) at the cost of visible structure.

The `-lavfi` flag enables the `lavfi` (libavfilter) virtual device as a filtergraph input, which is required when the filtergraph references multiple input streams with `[0:v]` and `[1:v]` style stream specifiers. Without `-lavfi`, the second input (the palette PNG) cannot be referenced in the filtergraph.

## Sources

- pkh.me — "High quality GIF with FFmpeg" (the definitive GIF guide): http://blog.pkh.me/p/21-high-quality-gif-with-ffmpeg.html
- Shotstack — "FFmpeg: MP4 to GIF Guide": https://shotstack.io/learn/convert-video-gif-ffmpeg/
- Bannerbear — "How to Make a GIF from a Video Using FFmpeg": https://www.bannerbear.com/blog/how-to-make-a-gif-from-a-video-using-ffmpeg/
- gifgen GitHub — shell script using the two-pass approach: https://github.com/lukechilds/gifgen

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
