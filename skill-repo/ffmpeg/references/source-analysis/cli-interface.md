# ffmpeg CLI Interface

## Invocation Patterns

### Single input, single output (most common)
```bash
ffmpeg -i input.mp4 [filters] [codec options] output.mp4
```

### Fast seeking (put -ss before -i)
```bash
ffmpeg -ss 00:01:00 -i input.mp4 -to 00:02:00 [options] output.mp4
```

### Multi-input (requires -filter_complex and -map)
```bash
ffmpeg -i video.mp4 -i audio.aac -filter_complex "..." -map "[v]" -map "[a]" output.mp4
```

### Pipe to null (analysis only, no output file)
```bash
ffmpeg -i input.mp4 -af "loudnorm=print_format=json" -f null -
```

### Batch via shell loop
```bash
for f in *.mov; do ffmpeg -nostdin -i "$f" [options] "${f%.mov}.mp4"; done
```

## ffprobe Patterns

### JSON output (best for scripting)
```bash
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4
```

### Specific field extraction
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 input.mp4
```

## Error Handling

ffmpeg exit codes:
- 0 = success
- 1 = generic error (check stderr)
- 69 = unavailable (codec not compiled in)

Always capture stderr — ffmpeg writes progress and errors there, not stdout.

## Platform Notes

- Windows: use forward slashes in paths or escape backslashes. Use `NUL` instead of `/dev/null`.
- macOS: ffmpeg from Homebrew includes most codecs. The Apple Silicon build includes VideoToolbox.
- Linux: distribution builds may lack non-free codecs (libfdk_aac, libx264). Use static builds from https://johnvansickle.com/ffmpeg/ for full codec support.
