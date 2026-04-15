# Hardware Encoding

## When to Use

Use hardware encoding when you need to encode video significantly faster than software (CPU) encoding allows — for real-time transcoding, batch processing large volumes, live streaming, or any situation where encode time is more important than achieving the absolute smallest file size.

Hardware encoders (NVENC, VAAPI, VideoToolbox) are 5–20x faster than equivalent software encodes, but they produce larger files at the same visual quality. A software encode at CRF 23 (`libx264`) will typically produce a 30–50% smaller file than NVENC at a comparable quality setting. This is an intentional tradeoff — hardware encoders prioritize throughput.

Choose based on your system:
- **NVIDIA GPU (Windows/Linux)** — use NVENC
- **Intel/AMD GPU on Linux** — use VAAPI
- **Apple Silicon or Intel Mac** — use VideoToolbox

## Technique

### NVENC (NVIDIA)

NVENC requires:
- An NVIDIA GPU (Kepler or newer for H.264; Maxwell or newer for HEVC; Turing or newer for AV1)
- NVIDIA drivers installed
- FFmpeg compiled with NVENC support (standard in most builds)

Key flags:
- `-hwaccel cuda` — enables CUDA hardware acceleration for decoding
- `-hwaccel_output_format cuda` — keeps decoded frames on the GPU, avoiding CPU↔GPU memory transfer between decode and encode
- `-rc vbr` — Variable Bitrate mode (recommended over CBR for quality)
- `-cq 23` — Constant Quality value (analogous to CRF; 0–51, lower=better)
- `-preset p1–p7` — p1 is fastest (lowest quality), p7 is slowest (highest quality). Default is p4 (medium)
- `-tune hq` — enables high-quality encoding optimizations
- `-profile:v high` — use High profile for H.264 (supports B-frames, better compression)

NVENC presets map roughly to:
| Preset | Description |
|--------|-------------|
| p1 | Fastest, lowest quality |
| p2 | Fast |
| p3 | Balanced fast |
| p4 | Default balance |
| p5 | Balanced quality |
| p6 | Slow, high quality |
| p7 | Slowest, highest quality |

### VAAPI (Linux — Intel/AMD)

VAAPI requires:
- Linux with VA-API drivers installed (Intel: intel-media-driver or i965-va-driver; AMD: mesa)
- The render device: typically `/dev/dri/renderD128`
- FFmpeg compiled with VAAPI support

The VAAPI upload pipeline requires an explicit filter chain to convert frames to the hardware format:
```
-vf 'format=nv12,hwupload'
```
`format=nv12` converts the pixel format to NV12 (the format VAAPI hardware expects), then `hwupload` transfers the frames to the GPU.

Key flags:
- `-vaapi_device /dev/dri/renderD128` — specify the hardware device
- `-qp 19` — quantization parameter (analogous to CRF; lower=better quality; typical range 18–28)
- `-profile:v high` / `-profile:v main` — profile selection (H.264 High, HEVC Main)

If you have multiple GPUs or render nodes, you may need `/dev/dri/renderD129` or another device.

### VideoToolbox (macOS/Apple Silicon)

VideoToolbox is Apple's hardware encode/decode framework, built into macOS and available on both Apple Silicon and Intel Macs.

Key flags:
- `-c:v h264_videotoolbox` or `-c:v hevc_videotoolbox`
- `-q:v 65` — quality setting on a 0–100 scale (higher=better; 65 is roughly equivalent to CRF 23)
- `-profile:v high` — for H.264 (`100` in some versions of FFmpeg — see note below)
- `-allow_sw 1` — fallback to software encoding if hardware is unavailable (useful in scripts)

**Note on profile for VideoToolbox:** Depending on your FFmpeg build, `-profile:v high` may need to be specified as `-profile:v 100` (the numeric H.264 profile value) for VideoToolbox. Check your FFmpeg version's behavior. For HEVC, `-profile:v main` is the standard choice.

VideoToolbox quality scale:
| `-q:v` | Approximate quality |
|--------|---------------------|
| 100 | Highest quality (near-lossless) |
| 65–75 | High quality (recommended) |
| 50 | Medium quality |
| 25 | Low quality |
| 0 | Lowest quality |

**Common mistakes:**
- Using `-hwaccel cuda` without `-hwaccel_output_format cuda` — frames are decoded on GPU but then copied to CPU and back to GPU for encoding, negating the memory bandwidth benefit
- Specifying an NVENC preset by name (`slow`, `medium`) instead of using `p1–p7` — the old preset names are deprecated and may behave unexpectedly in newer FFmpeg builds
- Forgetting the VAAPI filter chain (`format=nv12,hwupload`) — the encode will fail or fall back to software
- Using the wrong render device path on VAAPI systems with multiple GPUs — check with `ls /dev/dri/`
- Expecting hardware encode to match software encode quality at the same CRF/QP — hardware encoders are less efficient; use a lower QP (e.g., QP 19 on VAAPI vs CRF 23 on libx264) to get comparable quality
- Using VideoToolbox in scripts without `-allow_sw 1` — scripts will fail on machines without Apple GPU or when the hardware encoder is busy

## CLI Commands

### NVENC

**H.264 NVENC (GPU decode + encode, high quality):**
```bash
ffmpeg -hwaccel cuda -hwaccel_output_format cuda \
  -i input.mp4 \
  -c:v h264_nvenc -rc vbr -cq 23 -preset p6 -tune hq \
  -profile:v high -b:v 0 \
  -c:a aac -b:a 192k \
  -pix_fmt yuv420p -movflags +faststart \
  output_nvenc_h264.mp4
```

**HEVC NVENC (H.265 on GPU, ~50% smaller than H.264 at same quality):**
```bash
ffmpeg -hwaccel cuda -hwaccel_output_format cuda \
  -i input.mp4 \
  -c:v hevc_nvenc -rc vbr -cq 28 -preset p6 -tune hq \
  -profile:v main \
  -c:a aac -b:a 192k \
  -tag:v hvc1 -movflags +faststart \
  output_nvenc_hevc.mp4
```

### VAAPI

**H.264 VAAPI (Linux, Intel/AMD GPU):**
```bash
ffmpeg -vaapi_device /dev/dri/renderD128 \
  -i input.mp4 \
  -vf 'format=nv12,hwupload' \
  -c:v h264_vaapi -qp 19 -profile:v high \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  output_vaapi_h264.mp4
```

**HEVC VAAPI (Linux, Intel/AMD GPU):**
```bash
ffmpeg -vaapi_device /dev/dri/renderD128 \
  -i input.mp4 \
  -vf 'format=nv12,hwupload' \
  -c:v hevc_vaapi -qp 24 -profile:v main \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  output_vaapi_hevc.mp4
```

### VideoToolbox

**H.264 VideoToolbox (macOS):**
```bash
ffmpeg -i input.mp4 \
  -c:v h264_videotoolbox -q:v 65 -profile:v high \
  -allow_sw 1 \
  -c:a aac -b:a 192k \
  -pix_fmt yuv420p -movflags +faststart \
  output_vt_h264.mp4
```

**HEVC VideoToolbox (macOS, Apple Silicon native):**
```bash
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox -q:v 65 -profile:v main \
  -allow_sw 1 \
  -c:a aac -b:a 192k \
  -tag:v hvc1 -movflags +faststart \
  output_vt_hevc.mp4
```

## Under the Hood

NVENC is a dedicated hardware block on NVIDIA GPUs — it runs entirely independently of the CUDA shader cores, meaning you can encode video at full speed while using the GPU for other compute or rendering tasks simultaneously. It implements a subset of the H.264 and HEVC standard that is optimized for throughput rather than compression efficiency. The `-cq` mode targets a constant quantization parameter per frame, similar to CRF, but the motion estimation is less sophisticated than x264/x265.

**Performance note on `-pix_fmt yuv420p` with CUDA:** When using `-hwaccel cuda -hwaccel_output_format cuda`, frames stay in GPU memory. Adding `-pix_fmt yuv420p` forces a GPU→CPU→GPU round trip for pixel format conversion, which can negate much of the speed benefit. Omit it when your source is already yuv420p (most H.264 content). Include it only when the source uses an incompatible format like yuv444p or 10-bit.

VAAPI (Video Acceleration API) is a Linux API that abstracts hardware video encode/decode capabilities. It works with Intel Quick Sync Video, AMD VCE/VCN, and some other hardware. The `hwupload` filter in the filter chain is necessary because FFmpeg's software decode produces frames in system RAM — `hwupload` transfers them to the GPU's memory before the hardware encoder can use them. `format=nv12` is required first because VAAPI hardware typically only accepts NV12 pixel format.

VideoToolbox is a macOS framework that wraps Apple's hardware video codec (part of the Neural Engine on Apple Silicon, or a dedicated hardware block on Intel Macs). Apple Silicon's Media Engine handles ProRes and H.264/HEVC encodes with exceptional efficiency. The `-tag:v hvc1` flag on HEVC output is important for Apple ecosystem compatibility — without it, HEVC in MP4 uses the `hev1` tag, which some Apple devices and QuickTime handle differently from `hvc1`.

## Sources

- NVIDIA — FFmpeg Transcoding Guide: https://developer.nvidia.com/blog/nvidia-ffmpeg-transcoding-guide/
- FFmpeg Wiki — Hardware Acceleration Intro: https://trac.ffmpeg.org/wiki/HWAccelIntro
- Apple — VideoToolbox Documentation: https://developer.apple.com/documentation/videotoolbox

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
