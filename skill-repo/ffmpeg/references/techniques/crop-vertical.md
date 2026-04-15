# Crop to Vertical (16:9 to 9:16)

## When to Use

Use this technique when repurposing landscape (16:9) footage for short-form vertical platforms: TikTok, Instagram Reels, YouTube Shorts. The target is 1080x1920. Two approaches exist: center-crop (loses the edges, fills the frame) or pad (shrinks the full frame and adds side bars).

## Technique

**Center crop approach** — most common for talking heads and action centered in frame:
1. `crop=ih*9/16:ih` — crops to a 9:16 portion centered in the frame. `ih` is input height; `ih*9/16` is the 9:16 width that fits within that height.
2. `scale=1080:1920` — scales the cropped result to the exact delivery size.

**Pad approach** — preserves the full landscape frame, adds vertical bars:
1. `scale=1080:-2` — shrink width to 1080px, height auto (will be ~607px for 16:9).
2. `pad=1080:1920:0:(oh-ih)/2` — center vertically on a 1920-tall canvas with bars top and bottom.

Always add `-movflags +faststart` for web delivery so the moov atom is at the front of the file.

## CLI Commands

**Center crop 16:9 to 9:16 at 1080x1920:**
```bash
ffmpeg -i input.mp4 \
  -vf "crop=ih*9/16:ih,scale=1080:1920" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -movflags +faststart \
  output_vertical.mp4
```

**Expression-based crop with explicit centering (same result, more readable):**
```bash
ffmpeg -i input.mp4 \
  -vf "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -movflags +faststart \
  output_vertical_centered.mp4
```
`(iw-ih*9/16)/2` explicitly calculates the horizontal offset to center the crop window.

**Pad approach (full frame letterboxed into 9:16):**
```bash
ffmpeg -i input.mp4 \
  -vf "scale=1080:-2,pad=1080:1920:0:(oh-ih)/2:black" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -movflags +faststart \
  output_padded_vertical.mp4
```

**Web-optimized with faster preset for quick turnaround:**
```bash
ffmpeg -i input.mp4 \
  -vf "crop=ih*9/16:ih,scale=1080:1920:flags=lanczos" \
  -c:v libx264 -crf 20 -preset fast -pix_fmt yuv420p \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  output_vertical_web.mp4
```

## Under the Hood

The `crop` filter parameters are `crop=w:h:x:y` where `x:y` is the top-left corner of the crop window. When `x` and `y` are omitted, FFmpeg defaults to centering (`(iw-w)/2` and `(ih-h)/2`). So `crop=ih*9/16:ih` is shorthand for a centered 9:16 crop.

The expression `ih*9/16` computes the target width as a fraction of the input height. For a 1920x1080 input: `1080 * 9/16 = 607.5` — FFmpeg truncates to `607`. The crop window is then 607x1080, which is a valid 9:16 crop of the original 1080-tall frame.

`-movflags +faststart` runs a post-processing pass that moves the MP4 `moov` atom to the beginning of the file. Browsers and mobile players start streaming immediately without needing to download the full file first.

## Sources

- vgmoose.dev: https://vgmoose.dev/blog/how-to-crop-landscape-169-videos-to-vertical-916-using-ffmpeg-for-youtube-shorts-or-tiktok-6898118583/
- Shotstack: https://shotstack.io/learn/crop-resize-videos-ffmpeg/
- Bannerbear: https://www.bannerbear.com/blog/how-to-crop-resize-a-video-using-ffmpeg/

## Learned from Usage

- The arithmetic expression `ih*9/16` uses integer truncation in FFmpeg — this can be off by a pixel. Use `trunc(ih*9/16/2)*2` to guarantee an even number if needed.
- For content where the subject isn't centered (e.g., interview with subject on the left), adjust the `x` offset manually: `crop=ih*9/16:ih:iw/4:0` shifts the crop window to the left quarter.
- `-movflags +faststart` requires a two-pass write; FFmpeg will fail if the output path isn't writable for the temp file.
- Platform safe zones: TikTok overlays UI at the bottom ~250px and top ~150px. Center important content between y=150 and y=1670 of the 1920-tall output.
