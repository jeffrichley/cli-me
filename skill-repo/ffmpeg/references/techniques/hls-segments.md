# HLS Segmentation

## When to Use

Use HLS segmentation when you need to deliver adaptive bitrate video to browsers, iOS devices, or any player that supports the HLS protocol (`.m3u8` playlists + `.ts` or `.mp4` segments). HLS is the right choice for:

- VOD delivery to Apple devices (HLS is required for native Safari/iOS playback)
- Multi-quality adaptive streaming where the player switches bitrates based on bandwidth
- Live streaming with a sliding window playlist
- CDN-based delivery where segments are cached independently

HLS is not ideal for ultra-low-latency use cases (use DASH with `-ldash` or dedicated protocols like SRT/WebRTC instead).

## Technique

The core constraint of HLS is **keyframe alignment**. Every segment boundary must fall on a keyframe. If it does not, players will either show artifacts at the switch point or fail to switch bitrates at all. You enforce this by:

1. Setting `-g` (GOP size in frames) to match your segment duration × frame rate. For 6-second segments at 30fps: `-g 180`. For 6-second segments at 24fps: `-g 144`. For 6-second segments at variable-rate content encoded to 30fps: use `-g 48 -keyint_min 48` with a shorter segment time and `-sc_threshold 0` to suppress scene-change keyframes.
2. Setting `-sc_threshold 0` to prevent the encoder from inserting extra keyframes at scene changes. Extra keyframes break the fixed-GOP assumption and cause misaligned segment boundaries.
3. Setting `-keyint_min` equal to `-g` to prevent the encoder from inserting keyframes more frequently than the GOP size.

For multi-quality output, `-var_stream_map` names each variant stream and maps it to a named output template. Audio and video can be split into separate groups or kept muxed.

**Segment format choices:**
- `mpegts` (default): maximum compatibility, required for live. Works everywhere including older devices.
- `fmp4`: smaller overhead, supports CMAF, required for DRM. Use `-hls_segment_type fmp4`.

**CBR for consistent CDN caching and buffer behavior:** use `-x264-params nal-hrd=cbr:force-cfr=1` combined with `-maxrate` and `-bufsize`. This forces constant frame rate and fills the bitrate pipe, which matters for broadcast-compliant delivery.

**Live sliding window:** `-hls_list_size 3` keeps only 3 segments in the playlist at a time. `-hls_flags delete_segments` removes old segment files from disk. Without `delete_segments`, disk fills up indefinitely.

## CLI Commands

### Single-quality VOD with keyframe-aligned mpegts segments

```bash
ffmpeg \
  -i input.mp4 \
  -c:v libx264 \
  -profile:v high \
  -level:v 4.0 \
  -preset slow \
  -crf 22 \
  -g 48 \
  -keyint_min 48 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 128k \
  -ar 48000 \
  -f hls \
  -hls_time 6 \
  -hls_playlist_type vod \
  -hls_flags independent_segments \
  -hls_segment_type mpegts \
  -hls_segment_filename "output_%03d.ts" \
  output.m3u8
```

### Multi-quality VOD (1080p / 720p / 480p) with mpegts, single pass

```bash
ffmpeg \
  -i input.mp4 \
  -filter_complex \
    "[0:v]split=3[v1][v2][v3]; \
     [v1]scale=1920:1080[v1out]; \
     [v2]scale=1280:720[v2out]; \
     [v3]scale=854:480[v3out]" \
  -map "[v1out]" -map 0:a \
  -map "[v2out]" -map 0:a \
  -map "[v3out]" -map 0:a \
  -c:v:0 libx264 -profile:v:0 high   -level:v:0 4.1 -preset slow -b:v:0 5000k -maxrate:v:0 5350k -bufsize:v:0 10000k -g:v:0 48 -keyint_min:v:0 48 -sc_threshold:v:0 0 \
  -c:v:1 libx264 -profile:v:1 high   -level:v:1 3.1 -preset slow -b:v:1 2800k -maxrate:v:1 2996k -bufsize:v:1 5600k  -g:v:1 48 -keyint_min:v:1 48 -sc_threshold:v:1 0 \
  -c:v:2 libx264 -profile:v:2 main   -level:v:2 3.0 -preset slow -b:v:2 1400k -maxrate:v:2 1498k -bufsize:v:2 2800k  -g:v:2 48 -keyint_min:v:2 48 -sc_threshold:v:2 0 \
  -c:a:0 aac -b:a:0 192k -ar:a:0 48000 \
  -c:a:1 aac -b:a:1 128k -ar:a:1 48000 \
  -c:a:2 aac -b:a:2 96k  -ar:a:2 48000 \
  -f hls \
  -hls_time 6 \
  -hls_playlist_type vod \
  -hls_flags independent_segments \
  -hls_segment_type mpegts \
  -hls_segment_filename "stream_%v/seg_%03d.ts" \
  -master_pl_name master.m3u8 \
  -var_stream_map "v:0,a:0,name:1080p v:1,a:1,name:720p v:2,a:2,name:480p" \
  stream_%v/playlist.m3u8
```

This produces:
```
master.m3u8
stream_1080p/playlist.m3u8  stream_1080p/seg_000.ts  ...
stream_720p/playlist.m3u8   stream_720p/seg_000.ts   ...
stream_480p/playlist.m3u8   stream_480p/seg_000.ts   ...
```

### Multi-quality VOD with fmp4 segments (CMAF-ready)

```bash
ffmpeg \
  -i input.mp4 \
  -filter_complex \
    "[0:v]split=3[v1][v2][v3]; \
     [v1]scale=1920:1080[v1out]; \
     [v2]scale=1280:720[v2out]; \
     [v3]scale=854:480[v3out]" \
  -map "[v1out]" -map 0:a \
  -map "[v2out]" -map 0:a \
  -map "[v3out]" -map 0:a \
  -c:v:0 libx264 -profile:v:0 high -level:v:0 4.1 -preset slow -crf:v:0 18 -g:v:0 48 -keyint_min:v:0 48 -sc_threshold:v:0 0 \
  -c:v:1 libx264 -profile:v:1 high -level:v:1 3.1 -preset slow -crf:v:1 20 -g:v:1 48 -keyint_min:v:1 48 -sc_threshold:v:1 0 \
  -c:v:2 libx264 -profile:v:2 main -level:v:2 3.0 -preset slow -crf:v:2 22 -g:v:2 48 -keyint_min:v:2 48 -sc_threshold:v:2 0 \
  -c:a:0 aac -b:a:0 192k -ar:a:0 48000 \
  -c:a:1 aac -b:a:1 128k -ar:a:1 48000 \
  -c:a:2 aac -b:a:2 96k  -ar:a:2 48000 \
  -f hls \
  -hls_time 6 \
  -hls_playlist_type vod \
  -hls_flags independent_segments \
  -hls_segment_type fmp4 \
  -hls_fmp4_init_filename "stream_%v/init.mp4" \
  -hls_segment_filename "stream_%v/seg_%03d.m4s" \
  -master_pl_name master.m3u8 \
  -var_stream_map "v:0,a:0,name:1080p v:1,a:1,name:720p v:2,a:2,name:480p" \
  stream_%v/playlist.m3u8
```

### CBR encoding for broadcast-compliant HLS

```bash
ffmpeg \
  -i input.mp4 \
  -c:v libx264 \
  -profile:v high \
  -level:v 4.0 \
  -preset medium \
  -b:v 5000k \
  -maxrate 5350k \
  -bufsize 10000k \
  -x264-params "nal-hrd=cbr:force-cfr=1" \
  -g 48 \
  -keyint_min 48 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 192k \
  -ar 48000 \
  -f hls \
  -hls_time 6 \
  -hls_playlist_type vod \
  -hls_flags independent_segments \
  -hls_segment_type mpegts \
  -hls_segment_filename "cbr_seg_%03d.ts" \
  cbr_output.m3u8
```

### Live streaming with sliding window (3-segment window)

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
  -g 48 \
  -keyint_min 48 \
  -sc_threshold 0 \
  -c:a aac \
  -b:a 128k \
  -ar 48000 \
  -f hls \
  -hls_time 6 \
  -hls_list_size 3 \
  -hls_flags delete_segments+independent_segments \
  -hls_segment_type mpegts \
  -hls_segment_filename "/var/hls/live/seg_%05d.ts" \
  /var/hls/live/live.m3u8
```

## Under the Hood

**How HLS works:** The muxer writes a playlist file (`.m3u8`) containing a list of segment URIs, each with a `#EXTINF` duration tag. Players download the playlist, buffer 2-3 segments, then continuously refetch the playlist (for live) or seek by calculating byte offsets (for VOD). The `#EXT-X-ENDLIST` tag marks a VOD playlist as complete; its absence signals live.

**Why `-g 48 -keyint_min 48 -sc_threshold 0` together:** `-g` is the maximum GOP size. `-keyint_min` is the minimum. Setting them equal forces exactly one keyframe every 48 frames, no more, no less. `-sc_threshold 0` (the default in newer ffmpeg is actually `0`, but older builds default to `40`) prevents the encoder from detecting scene changes and inserting bonus keyframes that would misalign segment cuts. Without these three flags together, segment durations vary unpredictably and multi-quality playlists go out of sync.

**`-hls_flags independent_segments`:** Adds the `#EXT-X-INDEPENDENT-SEGMENTS` tag to the master playlist. This signals that every segment starts with a keyframe and can be decoded without reference to previous segments. Required for correct ABR switching.

**fmp4 segments:** Fragmented MP4 segments (`.m4s`) are part of the CMAF (Common Media Application Format) standard. They require an initialization segment (`init.mp4`) that contains the codec configuration box (`moov` with an empty `mdat`). Subsequent segments contain only media data. fmp4 is more efficient than mpegts (no 188-byte TS packet overhead) and is DRM-compatible.

**`-hls_list_size` and `-hls_flags delete_segments`:** In live mode, `hls_list_size` controls how many segments appear in the playlist at once (the sliding window). A value of 3 with 6-second segments gives 18 seconds of buffer. `delete_segments` removes segment files from disk when they scroll out of the playlist — critical for long-running streams to avoid filling the filesystem.

**`nal-hrd=cbr:force-cfr=1`:** These x264 parameters enforce constant bitrate at the Network Abstraction Layer level. `nal-hrd=cbr` fills the bitstream to exactly `maxrate` with filler NAL units, making every second of encoded video a fixed size. `force-cfr=1` forces constant frame rate, which is necessary because CBR assumes a fixed number of frames per second to maintain a stable buffer model. This is required for SCTE-35 ad insertion compatibility and some broadcast delivery specs.

## Sources

- [OTTVerse: HLS Packaging with FFmpeg](https://ottverse.com/hls-packaging-using-ffmpeg-live-vod/)
- [Mux: HLS Video Segmentation](https://www.mux.com/articles/hls-video-segmentation)
- [FFmpeg HLS Muxer Documentation](https://ffmpeg.org/ffmpeg-formats.html#hls-2)
- [FFmpeg x264 Encoding Guide](https://trac.ffmpeg.org/wiki/Encode/H.264)

## Learned from Usage

- Always set `-g`, `-keyint_min`, and `-sc_threshold 0` together. Missing any one of them causes intermittent segment misalignment that is hard to reproduce and hard to debug.
- When using `-var_stream_map`, the output filename template must contain `%v` as a stream index placeholder. Forgetting this causes ffmpeg to overwrite all streams into the same file.
- `fmp4` segments require the init file to be served with the correct MIME type (`video/mp4`) and the segments with `video/iso.segment`. Some CDNs need explicit MIME type configuration.
- For live output, use `-hls_flags delete_segments+independent_segments` (joined with `+`) not as separate flags.
- When ingesting from a camera or capture card, add `-vsync cfr` before the output flags to force constant frame rate — variable frame rate input with CBR encoding causes encoder buffer underflow warnings.
