# ffmpeg Knowledge Base

## Source Analysis
- [Analyzed Version](source-analysis/analyzed-version.md) — analysis metadata
- [API Surface](source-analysis/api-surface.md) — ffmpeg flags, filters, codecs
- [CLI Interface](source-analysis/cli-interface.md) — invocation patterns, ffprobe
- [Changelog](source-analysis/changelog.md) — version deltas

## Techniques — Convert & Compress
- [Convert Video Format](techniques/convert-video-format.md) — MOV/AVI/MKV to MP4
- [Compress Video](techniques/compress-video.md) — CRF tuning, two-pass
- [Convert Audio Format](techniques/convert-audio-format.md) — WAV/FLAC to MP3/AAC
- [Platform Encoding](techniques/platform-encoding.md) — YouTube, Twitter, TikTok specs
- [Hardware Encoding](techniques/hardware-encoding.md) — NVENC, VAAPI, VideoToolbox

## Techniques — Trim & Extract
- [Trim/Clip Video](techniques/trim-clip.md) — cut by timestamp
- [Extract Audio](techniques/extract-audio.md) — rip audio track
- [Extract Frames](techniques/extract-frames.md) — thumbnails, every Nth frame
- [Sprite Sheet](techniques/sprite-sheet.md) — tiled preview image
- [Surveillance Clip](techniques/surveillance-clip.md) — extract from rolling archive

## Techniques — Transform & Filter
- [Resize/Scale](techniques/resize-scale.md) — resolution changes
- [Crop to Vertical](techniques/crop-vertical.md) — landscape to 9:16
- [Change Speed](techniques/change-speed.md) — slow-mo, fast-forward, timelapse
- [Watermark Overlay](techniques/watermark-overlay.md) — logo/branding
- [Burn Subtitles](techniques/burn-subtitles.md) — SRT/ASS hardcoding
- [Rotate/Flip](techniques/rotate-flip.md) — orientation fixes
- [Fade Transitions](techniques/fade-transitions.md) — fade in/out

## Techniques — Audio Processing
- [Normalize Loudness](techniques/normalize-loudness.md) — EBU R128, LUFS
- [Remove Silence](techniques/remove-silence.md) — dead air trimming
- [Denoise Audio](techniques/denoise-audio.md) — background noise removal
- [Music Ducking](techniques/music-ducking.md) — mix music under voiceover

## Techniques — Combine & Assemble
- [Concatenate Clips](techniques/concatenate-clips.md) — join multiple videos
- [Mux Audio + Video](techniques/mux-audio-video.md) — combine separate tracks
- [Image Sequence to Video](techniques/image-sequence-to-video.md) — animation/timelapse
- [Complex Filtergraph](techniques/complex-filtergraph.md) — PiP, side-by-side, grid

## Techniques — Streaming & Distribution
- [HLS Segments](techniques/hls-segments.md) — adaptive .m3u8 + .ts
- [DASH Segments](techniques/dash-segments.md) — .mpd + .m4s
- [Multi-Bitrate](techniques/multi-bitrate.md) — adaptive bitrate ladder
- [RTMP Restream](techniques/rtmp-restream.md) — fan-out to multiple platforms
- [Fake Live Stream](techniques/fake-live-stream.md) — pre-recorded as live

## Techniques — Utilities
- [Batch Transcode](techniques/batch-transcode.md) — directory processing
- [ffprobe Validate](techniques/ffprobe-validate.md) — probe and compliance
- [RTSP Recording](techniques/rtsp-recording.md) — surveillance camera capture
- [Video to GIF](techniques/video-to-gif.md) — palette-optimized conversion
- [Screen Capture](techniques/screen-capture.md) — desktop recording

## Operational
- [Gotchas](gotchas.md) — cross-cutting issues and workarounds
- [Learning Log](log.md) — chronological record of learnings
