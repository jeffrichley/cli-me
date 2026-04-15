# Platform Encoding

## When to Use

Use this technique when encoding video specifically for upload to YouTube, Twitter/X, or TikTok. Each platform has its own ingest specifications and re-encodes uploaded content on its servers. The goal of platform encoding is not to produce the "final" video — it is to produce a source that the platform's encoder can process cleanly, avoiding double-compression artifacts and maximizing quality after the platform's own transcode pass.

Uploading a poorly-encoded source means the platform re-encodes already-degraded content, compounding quality loss. Uploading a well-encoded source (or a lossless one) gives the platform encoder the best possible input.

## Technique

### General Principles

- **Upload the highest quality you can afford** — platforms re-encode everything. A higher-quality upload = better platform output.
- **H.264 is the universally safe codec** — all platforms accept it. H.265 and VP9 are accepted by YouTube but not consistently by Twitter/X or TikTok.
- **`-pix_fmt yuv420p` is mandatory for all platforms** — without it, some platforms reject the upload outright; others transcode incorrectly.
- **`-movflags +faststart`** — required for MP4 uploads to ensure the file can be read by ingest systems before fully downloading.

### YouTube

YouTube recommends H.264 with the High profile for standard uploads. Key settings:
- Video: H.264 High profile, `-g 30` (keyframe every 30 frames / 1 second at 30fps), `-bf 2` (2 B-frames)
- Audio: AAC stereo, 384 kbps, 48 kHz sample rate
- Container: MP4
- YouTube processes uploads at the uploaded resolution and generates multiple quality tiers (1080p, 720p, etc.) automatically
- For 4K uploads, YouTube prefers VP9 on its CDN, but H.264 uploads are fine — YouTube will transcode to VP9 for delivery

YouTube also accepts ProRes, HEVC, VP9, and DNxHD for highest-quality ingest if you have those sources available.

### Twitter/X

Twitter/X has strict technical requirements and will reject or badly transcode files that don't conform:
- Video: H.264 High profile, **level 4.0** (important — level 4.1+ may be rejected)
- `-pix_fmt yuv420p` is mandatory — Twitter explicitly rejects yuv422p and yuv444p
- Maximum resolution: 1920×1200 (landscape) or 1200×1920 (portrait)
- Maximum file size: 512 MB
- Maximum duration: 2 minutes 20 seconds (140 seconds)
- Audio: AAC, 128 kbps minimum, 44.1 kHz or 48 kHz

Twitter re-encodes everything at lower bitrates for delivery, so there is no benefit to uploading above ~8 Mbps for 1080p.

### TikTok

TikTok is portrait-first (9:16 aspect ratio, 1080×1920). Key settings:
- Resolution: 1080×1920 (portrait) — landscape content gets letterboxed or cropped
- Video: H.264 High profile, **level 4.2**, 30fps
- Audio: AAC stereo, 256 kbps, **44.1 kHz** (TikTok is unusual in preferring 44.1 kHz over 48 kHz)
- Container: MP4
- Maximum file size: 287.6 MB for the TikTok app; 500 MB for Creator tools
- TikTok heavily compresses delivery; upload at the highest bitrate allowed

**Common mistakes:**
- Using the wrong H.264 level for Twitter (4.1+ causes rejection) — always specify `-profile:v high -level 4.0`
- Encoding at 48 kHz for TikTok when TikTok prefers 44.1 kHz — use `-ar 44100`
- Uploading landscape (16:9) content to TikTok without cropping to portrait — it will be letterboxed with large black bars
- Omitting `-pix_fmt yuv420p` — platforms silently degrade or reject non-yuv420p content
- Using a variable frame rate (VFR) source — some platforms, especially TikTok and Twitter, reject or incorrectly handle VFR. Use `-vsync cfr` or `-fps_mode cfr` to force constant frame rate

## CLI Commands

**YouTube — 1080p H.264 upload-ready:**
```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -profile:v high -crf 18 -preset slow \
  -g 30 -bf 2 \
  -c:a aac -b:a 384k -ar 48000 -ac 2 \
  -pix_fmt yuv420p -movflags +faststart \
  youtube_output.mp4
```

**YouTube — 4K (2160p) H.264 upload-ready:**
```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -profile:v high -crf 18 -preset slow \
  -vf scale=3840:2160 \
  -g 30 -bf 2 \
  -c:a aac -b:a 384k -ar 48000 -ac 2 \
  -pix_fmt yuv420p -movflags +faststart \
  youtube_4k_output.mp4
```

**Twitter/X — 720p safe default (recommended):**
```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -profile:v high -level:v 4.0 -crf 23 -preset medium \
  -vf "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2" \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  -pix_fmt yuv420p -movflags +faststart \
  twitter_output.mp4
```

720p is the safe default — Twitter's re-compression is less aggressive at this resolution,
and most Twitter video is consumed on mobile where 720p is indistinguishable from 1080p.
For 1080p output, use the YouTube preset or encode manually with `scale=1920:1080`.

**Twitter/X — from VFR source (force constant frame rate):**
```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -profile:v high -level:v 4.0 -crf 23 -preset medium \
  -vf "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2" \
  -fps_mode cfr -r 30 \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  -pix_fmt yuv420p -movflags +faststart \
  twitter_output.mp4
```

**TikTok — 1080×1920 portrait (from portrait source):**
```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -profile:v high -level 4.2 -crf 18 -preset slow \
  -vf scale=1080:1920 -r 30 \
  -c:a aac -b:a 256k -ar 44100 -ac 2 \
  -pix_fmt yuv420p -movflags +faststart \
  tiktok_output.mp4
```

**TikTok — 1080×1920 portrait (crop from 16:9 landscape source):**
```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -profile:v high -level 4.2 -crf 18 -preset slow \
  -vf "crop=ih*9/16:ih,scale=1080:1920" -r 30 \
  -c:a aac -b:a 256k -ar 44100 -ac 2 \
  -pix_fmt yuv420p -movflags +faststart \
  tiktok_cropped_output.mp4
```

## Under the Hood

Every major platform runs a transcoding pipeline on ingest. YouTube uses VP9 and AV1 for delivery (stored in multiple quality tiers); Twitter/X uses H.264 at constrained bitrates; TikTok uses H.264 and H.265 depending on the viewer's device.

The `-g` (GOP size / keyframe interval) setting controls how often I-frames (full frames) appear in the stream. YouTube recommends one per second (30 at 30fps) to enable efficient seeking and adaptive bitrate switching. Shorter GOP means more I-frames, larger file size, better seek performance. Longer GOP means fewer I-frames, smaller file, worse seek.

`-bf 2` sets the number of B-frames (bidirectionally predicted frames). B-frames reference both past and future frames for prediction, improving compression efficiency. The High profile supports B-frames; the Baseline profile does not. YouTube and TikTok both accept High profile.

H.264 levels define limits on resolution, frame rate, and bitrate. Level 4.0 supports up to 1080p@30fps with a 20 Mbps maximum bitrate. Level 4.1 and 4.2 extend these limits. Twitter's documented maximum is level 4.0 — exceeding it causes ingest rejection.

## Sources

- YouTube — Recommended Upload Encoding Settings: https://support.google.com/youtube/answer/1722171
- Twitter/X — Video Specifications: https://developer.twitter.com/en/docs/twitter-api/v1/media/upload-media/api-reference/post-media-upload
- TikTok — Video Size & Dimensions Guide: https://fliki.ai/blog/tiktok-video-size

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
