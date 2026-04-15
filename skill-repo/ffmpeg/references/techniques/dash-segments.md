# DASH Segmentation

## When to Use

Use DASH (Dynamic Adaptive Streaming over HTTP) when you need:

- **Adaptive bitrate streaming on Android or desktop Chrome/Firefox** — DASH has better native support in non-Apple ecosystems than HLS
- **CMAF dual-output** — a single set of fmp4 segments served with both an MPD (DASH) and M3U8 (HLS) manifest, cutting storage roughly in half
- **Low-latency live streaming** — DASH with `-ldash 1 -streaming 1` achieves 2-4 second latency vs HLS's typical 15-30 seconds
- **Separate audio adaptation sets** — DASH natively models audio and video as separate adaptation sets, enabling audio-only tracks and multi-language audio without hacking the video manifest
- **DRM / encrypted delivery** — DASH + CENC is the standard for multi-DRM (Widevine + PlayReady) delivery

Do not use plain DASH for Apple device delivery without CMAF dual-output — Safari and iOS require HLS manifests.

## Technique

The DASH muxer writes an MPD (Media Presentation Description) XML manifest and a set of segment files. The key structural concept is **adaptation sets**: groups of representations (bitrate variants) that differ only in quality, not content type. Video variants go in one set, audio variants in another.

**Keyframe alignment is mandatory in DASH, just as in HLS.** The segment duration (`-seg_duration 4`) must align with the GOP size. For 4-second segments at 30fps, use `-g 120 -keyint_min 120 -sc_threshold 0`. For 4-second segments at 24fps, use `-g 96 -keyint_min 96 -sc_threshold 0`.

**Template-based addressing** (`-use_template 1`) generates segments named by a template such as `chunk_$RepresentationID$_$Number%05d$.m4s`. This is more CDN-friendly than listing every segment URL in the MPD.

**Timeline** (`-use_timeline 1`) adds an `<SegmentTimeline>` element to the MPD, which records the actual duration of each segment. Required for VOD with variable-duration segments. For live with fixed-duration segments you can omit it, but it is safer to leave it on.

**Init segment:** Each representation has an initialization segment (default name: `init-stream$RepresentationID$.m4s`) containing the codec parameters. This must be fetched before any media segment can be decoded.

**CMAF dual-output** uses `-hls_playlist 1` to make the DASH muxer simultaneously write both an MPD and per-representation HLS playlists. The same fmp4 segment files are referenced by both manifests. This is the modern approach for multi-platform delivery.

**Low-latency DASH:** `-ldash 1` enables low-latency DASH extensions (chunk-transfer encoding, `availabilityTimeOffset` in MPD). `-streaming 1` enables streaming output mode where ffmpeg writes segments incrementally rather than buffering. Combine with `-window_size` to control playlist length.

## CLI Commands

### Multi-bitrate VOD (4 qualities) with separate audio adaptation set

```bash
ffmpeg \
  -i input.mp4 \
  -filter_complex \
    "[0:v]split=4[v1][v2][v3][v4]; \
     [v1]scale=1920:1080[v1out]; \
     [v2]scale=1280:720[v2out]; \
     [v3]scale=854:480[v3out]; \
     [v4]scale=640:360[v4out]" \
  -map "[v1out]" \
  -map "[v2out]" \
  -map "[v3out]" \
  -map "[v4out]" \
  -map 0:a \
  -c:v:0 libx264 -profile:v:0 high   -level:v:0 4.1 -preset slow -b:v:0 5000k -maxrate:v:0 5350k -bufsize:v:0 10000k -g:v:0 120 -keyint_min:v:0 120 -sc_threshold:v:0 0 \
  -c:v:1 libx264 -profile:v:1 high   -level:v:1 3.1 -preset slow -b:v:1 2800k -maxrate:v:1 2996k -bufsize:v:1 5600k  -g:v:1 120 -keyint_min:v:1 120 -sc_threshold:v:1 0 \
  -c:v:2 libx264 -profile:v:2 main   -level:v:2 3.0 -preset slow -b:v:2 1400k -maxrate:v:2 1498k -bufsize:v:2 2800k  -g:v:2 120 -keyint_min:v:2 120 -sc_threshold:v:2 0 \
  -c:v:3 libx264 -profile:v:3 baseline -level:v:3 3.0 -preset slow -b:v:3 800k  -maxrate:v:3 856k  -bufsize:v:3 1600k  -g:v:3 120 -keyint_min:v:3 120 -sc_threshold:v:3 0 \
  -c:a:0 aac -b:a:0 192k -ar:a:0 48000 \
  -f dash \
  -seg_duration 4 \
  -use_template 1 \
  -use_timeline 1 \
  -init_seg_name "init-\$RepresentationID\$.m4s" \
  -media_seg_name "chunk-\$RepresentationID\$-\$Number%05d\$.m4s" \
  -adaptation_sets "id=0,streams=v id=1,streams=a" \
  output.mpd
```

This produces:
```
output.mpd
init-stream0.m4s  init-stream1.m4s  init-stream2.m4s  init-stream3.m4s  init-stream4.m4s
chunk-stream0-00001.m4s  chunk-stream1-00001.m4s  ...
```

### Live DASH with low-latency extensions

```bash
ffmpeg \
  -i rtmp://localhost/live/stream \
  -c:v libx264 \
  -profile:v main \
  -level:v 3.1 \
  -preset ultrafast \
  -tune zerolatency \
  -b:v 2500k \
  -maxrate 2675k \
  -bufsize 5000k \
  -g 120 \
  -keyint_min 120 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 128k \
  -ar 48000 \
  -f dash \
  -seg_duration 4 \
  -use_template 1 \
  -use_timeline 1 \
  -streaming 1 \
  -ldash 1 \
  -window_size 5 \
  -extra_window_size 10 \
  -remove_at_exit 1 \
  -adaptation_sets "id=0,streams=v id=1,streams=a" \
  /var/dash/live/manifest.mpd
```

`-window_size 5` keeps 5 segments in the MPD. `-extra_window_size 10` keeps 10 extra segments on disk for late-joining clients. `-remove_at_exit 1` cleans up segment files when ffmpeg exits.

### CMAF dual-output: single fmp4 segments, both MPD and HLS manifests

```bash
ffmpeg \
  -i input.mp4 \
  -filter_complex \
    "[0:v]split=3[v1][v2][v3]; \
     [v1]scale=1920:1080[v1out]; \
     [v2]scale=1280:720[v2out]; \
     [v3]scale=854:480[v3out]" \
  -map "[v1out]" \
  -map "[v2out]" \
  -map "[v3out]" \
  -map 0:a \
  -c:v:0 libx264 -profile:v:0 high -level:v:0 4.1 -preset slow -crf:v:0 18 -g:v:0 120 -keyint_min:v:0 120 -sc_threshold:v:0 0 \
  -c:v:1 libx264 -profile:v:1 high -level:v:1 3.1 -preset slow -crf:v:1 20 -g:v:1 120 -keyint_min:v:1 120 -sc_threshold:v:1 0 \
  -c:v:2 libx264 -profile:v:2 main -level:v:2 3.0 -preset slow -crf:v:2 22 -g:v:2 120 -keyint_min:v:2 120 -sc_threshold:v:2 0 \
  -c:a:0 aac -b:a:0 192k -ar:a:0 48000 \
  -f dash \
  -seg_duration 4 \
  -use_template 1 \
  -use_timeline 1 \
  -hls_playlist 1 \
  -hls_playlist_type vod \
  -init_seg_name "init-\$RepresentationID\$.mp4" \
  -media_seg_name "seg-\$RepresentationID\$-\$Number%05d\$.m4s" \
  -adaptation_sets "id=0,streams=v id=1,streams=a" \
  cmaf/manifest.mpd
```

`-hls_playlist 1` instructs the DASH muxer to also write per-representation HLS playlists (`.m3u8` files) referencing the same `.m4s` segments. The master HLS playlist is written alongside `manifest.mpd` as `master.m3u8`.

### Multi-bitrate live with separate audio tracks (multi-language)

```bash
ffmpeg \
  -i input_with_two_audio_tracks.mkv \
  -filter_complex \
    "[0:v]split=2[v1][v2]; \
     [v1]scale=1920:1080[v1out]; \
     [v2]scale=1280:720[v2out]" \
  -map "[v1out]" \
  -map "[v2out]" \
  -map 0:a:0 \
  -map 0:a:1 \
  -c:v:0 libx264 -profile:v:0 high -level:v:0 4.1 -preset fast -b:v:0 5000k -g:v:0 120 -keyint_min:v:0 120 -sc_threshold:v:0 0 \
  -c:v:1 libx264 -profile:v:1 high -level:v:1 3.1 -preset fast -b:v:1 2800k -g:v:1 120 -keyint_min:v:1 120 -sc_threshold:v:1 0 \
  -c:a:0 aac -b:a:0 192k -ar:a:0 48000 -metadata:s:a:0 language=eng \
  -c:a:1 aac -b:a:1 192k -ar:a:1 48000 -metadata:s:a:1 language=spa \
  -f dash \
  -seg_duration 4 \
  -use_template 1 \
  -use_timeline 1 \
  -adaptation_sets "id=0,streams=v id=1,streams=a:0 id=2,streams=a:1" \
  multilang.mpd
```

The three adaptation sets produce three groups in the MPD: one for video (2 representations), one for English audio, one for Spanish audio.

## Under the Hood

**MPD structure:** The MPD is an XML file with a `<Period>` containing one or more `<AdaptationSet>` elements. Each `AdaptationSet` has multiple `<Representation>` elements (one per bitrate). The player downloads the MPD, picks representations based on available bandwidth, and fetches initialization + media segments for each chosen representation.

**Adaptation set separation (`id=0,streams=v id=1,streams=a`):** The syntax assigns ffmpeg output streams to named adaptation sets. `streams=v` matches all video streams; `streams=a` matches all audio streams. You can also use stream indices: `streams=0,1,2` for the first three output streams. The reason to separate audio from video is that DASH players can independently select audio and video representations — enabling audio-only playback modes and multi-language tracks.

**`-use_template 1` vs segment list:** Template mode generates `<SegmentTemplate>` elements with `$Number$` or `$Time$` variables. The player constructs segment URLs without needing a complete list, which keeps the MPD small and enables CDN prefetching. Without template mode, the MPD lists every segment URL explicitly, which becomes enormous for long content.

**`-use_timeline 1`:** Adds `<SegmentTimeline>` with explicit `<S>` (segment) elements recording actual durations. Without this, the MPD assumes all segments are exactly `seg_duration` long. For content with variable-length final segments (common in VOD), `use_timeline` is required for correct seeking.

**Init segment:** The init segment is a valid fMP4 file containing `ftyp`, `moov`, and an empty `mdat` box. It contains codec configuration (SPS/PPS for H.264, codec box for AAC) but no media samples. Clients must fetch this before any media segment. Re-requesting the init segment on stream switch is one source of ABR switch latency.

**`-ldash 1`:** Low-latency DASH (LL-DASH) adds `<ServiceDescription>` and `<ProducerReferenceTime>` elements to the MPD and enables chunk-transfer encoding so clients can start downloading a segment before it is complete. The player fetches each chunk in parallel with ongoing ingest. This requires a properly configured HTTP server that supports chunked transfer — nginx works; some CDNs require configuration.

**`-hls_playlist 1` (CMAF dual-output):** When this flag is set, the DASH muxer additionally writes per-representation M3U8 playlists where each `#EXTINF` line points to the same `.m4s` file referenced by the MPD. A master HLS playlist (`master.m3u8`) is written alongside the MPD. Both manifests share one set of segment files, so storage cost equals one copy instead of two.

## Sources

- [OTTVerse: HLS and MPEG-DASH ABR Packaging Overview](https://ottverse.com/abr-packaging-for-vod-live-hls-and-dash-overview/)
- [FFmpeg DASH Muxer Documentation](https://ffmpeg.org/ffmpeg-formats.html#dash-2)
- [GPAC Wiki: DASH Sequences and Examples](https://github.com/gpac/gpac/wiki/DASH-Sequences)
- [DASH Industry Forum: Guidelines for Implementation](https://dashif.org/guidelines/)

## Learned from Usage

- The `-adaptation_sets` string must use the exact syntax `"id=0,streams=v id=1,streams=a"` with a space (not comma) between sets. Getting this wrong produces a single adaptation set with everything muxed, which breaks audio-only switching.
- Dollar signs in `-init_seg_name` and `-media_seg_name` must be escaped as `\$` in shell to prevent variable expansion: `"\$RepresentationID\$"`.
- `-streaming 1` without `-ldash 1` still helps for live output because it writes the MPD incrementally. Use both together for true low-latency delivery.
- When outputting to a directory that does not exist, ffmpeg fails silently on some builds. Always `mkdir -p` the output directory first.
- CMAF dual-output with `-hls_playlist 1` writes the master HLS playlist as `master.m3u8` next to the MPD, regardless of what you name the MPD. Do not assume the HLS master will share the MPD's basename.
- For live streams, `-remove_at_exit 1` is important — without it, segment files accumulate indefinitely even after ffmpeg exits, and the MPD may reference stale segments if you restart the stream.
