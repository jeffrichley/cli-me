# Batch Transcode

## When to Use

Use this technique when you need to transcode more than one file — converting a folder of raw recordings, re-encoding an archive to a new codec, or normalizing a mixed-format library to a consistent output format. The key concerns are: preventing stdin from being consumed by the loop, skipping files that have already been converted, and using parallelism safely when the machine has headroom.

Use the basic loop for simple jobs. Use `find` with recursive traversal when files are in subdirectories. Use GNU `parallel` when you have multiple CPU cores to spare and the encode is CPU-bound. Use NVIDIA GPU batching when you have an NVIDIA GPU and the queue is very large.

## Technique

### The -nostdin Flag is Mandatory in Loops

When ffmpeg runs inside a shell loop, it will try to read from stdin (for interactive prompts like "overwrite?"). This consumes stdin from the loop itself, causing the loop to skip files or exit early. Always pass `-nostdin` to suppress this behavior.

### Skip-If-Exists Guard

Before running ffmpeg, check whether the output file already exists. This lets you safely resume interrupted batches without re-encoding files that completed successfully. Pair this with `-y` (auto-overwrite) only when you intentionally want to re-encode.

### Output Directory Pattern

Always define an output directory variable and create it with `mkdir -p` before the loop. Use parameter expansion (`"${f%.*}"`) to strip the source extension and construct the output filename.

### GNU Parallel

`parallel -j4` runs 4 jobs at once. Use `-j$(nproc)` to fill all CPU cores, or set a fixed number to leave headroom for other processes. Combine with `--eta` for progress estimates and `--joblog` for a resume-safe log. With parallel, each job must use `-nostdin` because parallel manages stdin itself.

### NVIDIA GPU Batch

Use `-hwaccel cuda -hwaccel_output_format cuda` to keep decoded frames on the GPU. Use `h264_nvenc` or `hevc_nvenc` as the encoder. The GPU encoder is much faster than CPU but typically produces larger files at equivalent perceived quality — it is best suited for archival speed, not maximum compression.

### Windows CMD (.bat files)

In a `.bat` file, loop variables use `%%f` (double percent). In the interactive CMD shell, use `%f` (single percent). This is a common source of broken batch scripts.

## CLI Commands

**Basic bash loop — transcode all MKV to MP4:**
```bash
mkdir -p output
for f in *.mkv; do
  ffmpeg -nostdin -i "$f" -c:v libx264 -crf 23 -preset medium \
    -c:a aac -b:a 192k "output/${f%.mkv}.mp4"
done
```

**Skip-if-exists guard + output directory:**
```bash
mkdir -p output
for f in *.mov; do
  out="output/${f%.mov}.mp4"
  if [ -f "$out" ]; then
    echo "Skipping $f (already exists)"
    continue
  fi
  ffmpeg -nostdin -i "$f" -c:v libx264 -crf 23 -preset medium \
    -c:a aac -b:a 192k "$out"
done
```

**Recursive transcode with find (all MP4 files under current directory):**
```bash
mkdir -p output
find . -name "*.mp4" -type f | while IFS= read -r f; do
  out="output/$(basename "${f%.mp4}").mp4"
  if [ ! -f "$out" ]; then
    ffmpeg -nostdin -i "$f" -c:v libx264 -crf 23 -preset medium \
      -c:a aac -b:a 192k "$out"
  fi
done
```

**GNU parallel — 4 concurrent jobs:**
```bash
mkdir -p output
find . -name "*.mkv" -type f | \
  parallel -j4 --eta \
    'ffmpeg -nostdin -i {} -c:v libx264 -crf 23 -preset medium \
     -c:a aac -b:a 192k "output/{/.}.mp4"'
```

**GNU parallel with job log (resume-safe):**
```bash
mkdir -p output
find . -name "*.mkv" -type f | \
  parallel -j4 --joblog transcode.log --resume \
    'ffmpeg -nostdin -i {} -c:v libx264 -crf 23 -preset medium \
     -c:a aac -b:a 192k "output/{/.}.mp4"'
```

**NVIDIA GPU batch (h264_nvenc):**
```bash
mkdir -p output
for f in *.mkv; do
  out="output/${f%.mkv}.mp4"
  [ -f "$out" ] && continue
  ffmpeg -nostdin -hwaccel cuda -hwaccel_output_format cuda \
    -i "$f" -c:v h264_nvenc -preset p4 -cq 23 \
    -c:a aac -b:a 192k "$out"
done
```

**PowerShell — basic loop:**
```powershell
New-Item -ItemType Directory -Force -Path output | Out-Null
Get-ChildItem -Filter *.mkv | ForEach-Object {
    $out = "output\$($_.BaseName).mp4"
    ffmpeg -nostdin -i $_.FullName -c:v libx264 -crf 23 -preset medium `
        -c:a aac -b:a 192k $out
}
```

**PowerShell — with error logging and skip-if-exists:**
```powershell
New-Item -ItemType Directory -Force -Path output | Out-Null
$log = "transcode_errors.txt"
Get-ChildItem -Filter *.mkv | ForEach-Object {
    $out = "output\$($_.BaseName).mp4"
    if (Test-Path $out) {
        Write-Host "Skipping $($_.Name) (already exists)"
        return
    }
    Write-Host "Transcoding $($_.Name)..."
    $result = ffmpeg -nostdin -i $_.FullName -c:v libx264 -crf 23 -preset medium `
        -c:a aac -b:a 192k $out 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-Content $log "FAILED: $($_.FullName)"
        Write-Warning "Failed: $($_.Name)"
    }
}
```

**Windows CMD .bat file (note double %% for loop variables):**
```bat
@echo off
if not exist output mkdir output
for %%f in (*.mkv) do (
    if not exist "output\%%~nf.mp4" (
        ffmpeg -nostdin -i "%%f" -c:v libx264 -crf 23 -preset medium ^
            -c:a aac -b:a 192k "output\%%~nf.mp4"
    )
)
```

## Under the Hood

The `-nostdin` flag redirects ffmpeg's stdin to `/dev/null` (or `NUL` on Windows) internally, preventing it from attempting to read interactive input. Without it, ffmpeg in a loop will read the next filename from the shell's stdin pipe, consuming it before the loop variable is assigned — causing unpredictable skips.

GNU `parallel` uses a semaphore-based job slot system. With `-j4`, it maintains up to 4 child processes at once, launching a new job as each slot frees. The `{/.}` substitution removes both the directory prefix and the file extension from the input filename, making it a clean basename for constructing output paths.

NVIDIA NVENC encodes on the GPU's dedicated video encode engine, which is separate from the CUDA cores used for compute. The `hwaccel_output_format cuda` option keeps decoded frames in GPU memory as a `cuda` format frame, avoiding a round-trip through system RAM. The `-cq` parameter (Constant Quality) is NVENC's equivalent of `-crf` — lower values mean higher quality.

## Sources

- OTTVerse — "FFmpeg Batch Processing": https://ottverse.com/ffmpeg-batch-processing/
- ffmpeg.media — "Batch Convert Videos": https://ffmpeg.media/batch-convert/
- streamingmedia — "Using FFmpeg for Batch Video Encoding": https://www.streamingmedia.com/
- randomblock1 — "Batch Transcoding with FFmpeg and GNU Parallel": https://randomblock1.com/

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
