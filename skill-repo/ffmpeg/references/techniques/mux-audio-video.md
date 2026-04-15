# Mux Audio and Video

## When to Use

Use muxing when you need to combine separate audio and video streams into a single file, replace the audio track in a video, add multiple language tracks, or synchronize audio to video with an offset correction.

If both streams already use codecs supported by the target container, use `-c copy` for a lossless, instant mux. Re-encode only when the codec or container requires it.

## Technique

**The `-map` flag is essential when working with multiple inputs.** Without it, FFmpeg auto-selects one stream per type from all inputs, which often picks the wrong stream. Be explicit.

**Lossless mux (`-c copy`):** Works when the codecs in both inputs are already compatible with the output container. No quality loss, nearly instant.

**Re-encode audio:** Required when the input audio codec is not compatible with the container (e.g., PCM WAV into MP4, which requires AAC or MP3).

**Looping music to match video duration:** Use `-stream_loop -1` before the audio `-i` to loop it indefinitely, and `-shortest` on the output to stop when the shorter stream (the video) ends.

**Sync correction with `-itsoffset`:** Place `-itsoffset <seconds>` immediately before the `-i` it applies to. Positive value delays that input. Use this to fix audio that arrives early or late relative to video.

**Multiple language tracks:** Add multiple `-i` audio inputs and use `-map` for each, then set metadata with `-metadata:s:a:N language=<iso639-2>`.

## CLI Commands

**Basic mux — combine separate video and audio files:**
```bash
ffmpeg -i video.mp4 -i audio.aac \
  -map 0:v -map 1:a \
  -c copy \
  output.mp4
```

**Replace audio — discard original audio from video:**
```bash
ffmpeg -i video.mp4 -i new_audio.aac \
  -map 0:v -map 1:a \
  -c copy \
  output.mp4
```

**Re-encode audio (e.g., WAV source into MP4):**
```bash
ffmpeg -i video.mp4 -i audio.wav \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k \
  output.mp4
```

**Multiple language audio tracks:**
```bash
ffmpeg -i video.mp4 -i english.aac -i french.aac \
  -map 0:v -map 1:a -map 2:a \
  -c copy \
  -metadata:s:a:0 language=eng \
  -metadata:s:a:1 language=fra \
  output.mp4
```

**Loop background music to match video length:**
```bash
ffmpeg -i video.mp4 -stream_loop -1 -i music.mp3 \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k \
  -shortest \
  output.mp4
```

**Delay audio by 1.5 seconds (audio arrives early — push it forward):**
```bash
ffmpeg -i video.mp4 -itsoffset 1.5 -i audio.aac \
  -map 0:v -map 1:a \
  -c copy \
  output.mp4
```

**Delay video by 0.5 seconds (audio arrives late — push video forward):**
```bash
ffmpeg -itsoffset 0.5 -i video.mp4 -i audio.aac \
  -map 0:v -map 1:a \
  -c copy \
  output.mp4
```

## Under the Hood

FFmpeg's muxer combines packet streams from multiple demuxers into a single output container. When you pass multiple `-i` inputs, FFmpeg assigns each an index (0, 1, 2…). The `-map 0:v` flag means "take the video stream from input 0"; `-map 1:a` means "take the audio stream from input 1."

`-c copy` (stream copy) passes encoded packets directly from demuxer to muxer without decoding or re-encoding. It is only valid when the codec is compatible with the output container.

`-stream_loop -1` tells the demuxer for that input to loop the file indefinitely. Combined with `-shortest`, FFmpeg stops writing output as soon as the shortest input stream is exhausted — effectively trimming the looped audio to match the video's duration.

`-itsoffset` injects a timestamp offset at the demuxer level, before packets are read. This shifts all timestamps for that input by the specified number of seconds, which is how FFmpeg implements A/V sync correction without re-encoding.

## Sources

- Mux — "How to Combine Audio and Video Files Using FFmpeg": https://www.mux.com/articles/merge-audio-and-video-files-with-ffmpeg
- Streaming Learning Center — "FFmpeg to the Rescue: Muxing Audio and Video Files": https://streaminglearningcenter.com/learning/ffmpeg-to-the-rescue-muxing-audio-and-video-files.html
- Filmora — "Mastering FFmpeg: How to Merge Audio and Video with Ease": https://filmora.wondershare.com/video-editor/ffmpeg-merge-audio-and-video.html

## Learned from Usage

- Forgetting `-map` with multiple inputs is the most common mux mistake — FFmpeg will silently pick streams you did not intend.
- `-c copy` will silently produce a broken file if the source codec is incompatible with the container (e.g., AC3 audio in an MP4). Always verify codec compatibility for the target container.
- `-itsoffset` must come immediately before the `-i` it modifies — order matters.
- When looping music, `-shortest` is mandatory or FFmpeg will loop forever waiting for the audio stream to end.
