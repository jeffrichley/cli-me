# Screen Capture

## When to Use

Use this technique when recording your screen to a video file — for tutorials, bug reports, demos, or archival. The input device is platform-specific: Linux uses `x11grab` (X11 sessions only, not Wayland), Windows uses `gdigrab` (legacy, all versions) or `ddagrab` (modern, Windows 8+, recommended), and macOS uses `avfoundation`. Audio capture requires a separate input device on all platforms.

For high frame rate capture (60fps+), consider a two-pass strategy: capture losslessly first, then encode to the target format. This avoids dropped frames caused by encoder latency during capture.

Always list available devices first to confirm device names before capturing.

## Technique

### Platform Overview

| Platform | Device | Notes |
|----------|--------|-------|
| Linux | `x11grab` | X11 only. Does NOT work on Wayland. Use `echo $WAYLAND_DISPLAY` to check. |
| Windows (legacy) | `gdigrab` | Works on all Windows. Captures the GDI layer — misses some GPU-accelerated content. |
| Windows (modern) | `ddagrab` | Windows 8+. Uses DXGI Desktop Duplication API. Captures GPU content correctly. Recommended. |
| macOS | `avfoundation` | Lists devices as numbered indices. Requires Screen Recording permission in System Preferences. |

### Audio is a Separate Input

On all platforms, audio is captured as an additional `-i` argument from a separate audio device, not from the screen capture device. Each platform uses a different audio device name. Combine screen and audio by specifying both inputs and mapping them.

### Two-Pass Strategy for High FPS

At high frame rates (60fps), the encoder may not keep up with the capture rate in real time, causing the capture device to drop frames. Capture losslessly first (to an intermediate file with `ffv1` or `utvideo` codec), then encode in a second step. This decouples capture speed from encode speed.

### Region Capture

All platforms support capturing a specific region instead of the full screen. Specify position (`x,y` offset from the top-left of the screen or display) and dimensions (`width x height`).

### Window Capture

Window capture (by title) is supported on Windows (`gdigrab` with `-i title=...`) and macOS (`avfoundation` with the window index). Linux `x11grab` captures by screen coordinates — use `xwininfo` to get the position and size of a specific window.

## CLI Commands

---

### Linux (x11grab — X11 only)

**List devices (X11 display):**
```bash
# Check X11 display
echo $DISPLAY
# Check if running Wayland (x11grab will NOT work if this is set)
echo $WAYLAND_DISPLAY
```

**Full screen capture:**
```bash
ffmpeg -f x11grab -r 30 -s 1920x1080 -i :0.0 \
  -c:v libx264 -preset ultrafast -crf 0 output.mkv
```

**With audio (ALSA):**
```bash
ffmpeg -f x11grab -r 30 -s 1920x1080 -i :0.0 \
  -f alsa -i default \
  -c:v libx264 -preset ultrafast -crf 23 \
  -c:a aac -b:a 192k output.mkv
```

**With audio (PulseAudio):**
```bash
ffmpeg -f x11grab -r 30 -s 1920x1080 -i :0.0 \
  -f pulse -i default \
  -c:v libx264 -preset ultrafast -crf 23 \
  -c:a aac -b:a 192k output.mkv
```

**Region capture (640x480 starting at x=100, y=200):**
```bash
ffmpeg -f x11grab -r 30 -s 640x480 -i :0.0+100,200 \
  -c:v libx264 -preset ultrafast -crf 23 output.mkv
```

**Window capture (get geometry with xwininfo first):**
```bash
# Get window position and size
xwininfo -name "Firefox"
# Then capture that region:
ffmpeg -f x11grab -r 30 -s WIDTHxHEIGHT -i :0.0+X,Y \
  -c:v libx264 -preset ultrafast -crf 23 output.mkv
```

**Hardware encoding with VAAPI (Intel/AMD GPU):**
```bash
ffmpeg -vaapi_device /dev/dri/renderD128 \
  -f x11grab -r 30 -s 1920x1080 -i :0.0 \
  -vf 'format=nv12,hwupload' \
  -c:v h264_vaapi -qp 24 output.mkv
```

**Lossless first-pass (then encode separately):**
```bash
# Pass 1: lossless capture
ffmpeg -f x11grab -r 60 -s 1920x1080 -i :0.0 \
  -c:v ffv1 -level 3 lossless_capture.mkv

# Pass 2: encode to delivery format
ffmpeg -i lossless_capture.mkv \
  -c:v libx264 -crf 23 -preset slow output.mp4
```

---

### Windows (gdigrab — legacy, all versions)

**List devices:**
```bash
ffmpeg -list_devices true -f dshow -i dummy 2>&1 | grep -i "directshow"
# For gdigrab, the desktop is always "desktop" — no listing needed
```

**Full screen capture (primary monitor):**
```bash
ffmpeg -f gdigrab -r 30 -i desktop \
  -c:v libx264 -preset ultrafast -crf 23 output.mkv
```

**With audio (DirectShow microphone):**
```bash
ffmpeg -f gdigrab -r 30 -i desktop \
  -f dshow -i audio="Microphone (Realtek Audio)" \
  -c:v libx264 -preset ultrafast -crf 23 \
  -c:a aac -b:a 192k output.mkv
```

**Region capture (offset 100,200, size 1280x720):**
```bash
ffmpeg -f gdigrab -r 30 -offset_x 100 -offset_y 200 \
  -video_size 1280x720 -i desktop \
  -c:v libx264 -preset ultrafast -crf 23 output.mkv
```

**Window capture by title:**
```bash
ffmpeg -f gdigrab -r 30 -i title="Notepad" \
  -c:v libx264 -preset ultrafast -crf 23 output.mkv
```

**Hardware encoding (NVIDIA NVENC):**
```bash
ffmpeg -f gdigrab -r 30 -i desktop \
  -c:v h264_nvenc -preset p4 -cq 23 output.mkv
```

---

### Windows (ddagrab — modern, Windows 8+, recommended)

**List displays (output_idx values):**
```bash
ffmpeg -f lavfi -i ddagrab=0 -vframes 1 -f null - 2>&1 | head -5
# output_idx=0 is the primary display; increment for additional monitors
```

**Full screen capture (primary display, GPU-accelerated):**
```bash
ffmpeg -f lavfi -i ddagrab=output_idx=0 \
  -c:v h264_nvenc -preset p4 -cq 23 output.mkv
```

**Full screen with audio:**
```bash
ffmpeg -f lavfi -i ddagrab=output_idx=0 \
  -f dshow -i audio="Microphone (Realtek Audio)" \
  -c:v h264_nvenc -preset p4 -cq 23 \
  -c:a aac -b:a 192k output.mkv
```

**Region capture (x=100, y=200, 1280x720):**
```bash
ffmpeg -f lavfi \
  -i "ddagrab=output_idx=0:offset_x=100:offset_y=200:video_size=1280x720" \
  -c:v h264_nvenc -preset p4 -cq 23 output.mkv
```

**Window capture (ddagrab captures full desktop; crop in filtergraph):**
```bash
# ddagrab captures the full display; use -vf crop for window region
ffmpeg -f lavfi -i ddagrab=output_idx=0 \
  -vf "crop=1280:720:100:200" \
  -c:v h264_nvenc -preset p4 -cq 23 output.mkv
```

**Lossless first-pass (software encode fallback):**
```bash
# Pass 1: lossless capture via ddagrab
ffmpeg -f lavfi -i ddagrab=output_idx=0 \
  -c:v ffv1 lossless_capture.mkv

# Pass 2: encode to delivery format
ffmpeg -i lossless_capture.mkv \
  -c:v libx264 -crf 23 -preset slow output.mp4
```

---

### macOS (avfoundation)

**List devices (required — device indices vary per machine):**
```bash
ffmpeg -f avfoundation -list_devices true -i "" 2>&1
# Video devices are listed as [0], [1], etc.
# Audio devices similarly numbered
# "Capture screen 0" is typically the primary display
```

**Full screen capture (screen index 1, adjust per list-devices output):**
```bash
ffmpeg -f avfoundation -r 30 -i "1" \
  -c:v libx264 -preset ultrafast -crf 23 output.mkv
```

**With audio (screen video + audio input device index 0):**
```bash
ffmpeg -f avfoundation -r 30 -i "1:0" \
  -c:v libx264 -preset ultrafast -crf 23 \
  -c:a aac -b:a 192k output.mkv
```

**Region capture (crop filter — avfoundation captures full screen):**
```bash
ffmpeg -f avfoundation -r 30 -i "1" \
  -vf "crop=1280:720:100:200" \
  -c:v libx264 -preset ultrafast -crf 23 output.mkv
```

**Window capture (use window index from list-devices):**
```bash
# List devices to find the window capture index
ffmpeg -f avfoundation -list_devices true -i "" 2>&1
# Then capture by index:
ffmpeg -f avfoundation -r 30 -i "2" \
  -c:v libx264 -preset ultrafast -crf 23 output.mkv
```

**Hardware encoding (VideoToolbox — Apple Silicon / Intel Mac):**
```bash
ffmpeg -f avfoundation -r 30 -i "1" \
  -c:v h264_videotoolbox -q:v 50 output.mkv
```

**Lossless first-pass:**
```bash
# Pass 1: lossless capture
ffmpeg -f avfoundation -r 60 -i "1" \
  -c:v ffv1 lossless_capture.mkv

# Pass 2: encode
ffmpeg -i lossless_capture.mkv \
  -c:v libx264 -crf 23 -preset slow output.mp4
```

---

## Under the Hood

**x11grab** uses the X11 XShmGetImage API to read the framebuffer directly from the X server's shared memory segment. It polls at the specified frame rate by sleeping between grabs. It operates entirely in CPU/system RAM and has no access to OpenGL or Vulkan framebuffers, meaning GPU-rendered overlays may not appear correctly.

**gdigrab** uses the Windows GDI BitBlt API to copy pixels from the screen's device context. Like x11grab, it operates on the GDI composited image and may miss Direct3D or DXGI content that bypasses GDI (hardware overlays, some games, some video players).

**ddagrab** uses the DXGI Desktop Duplication API (Windows 8+), which captures the composed desktop frame directly from the GPU's output, including all rendered content. It returns a `d3d11` or `cuda` format frame that can be passed directly to a hardware encoder without going through system RAM, making it both faster and more complete than gdigrab.

**avfoundation** uses Apple's AVFoundation framework, which on modern macOS routes through the ScreenCaptureKit API (macOS 12.3+) under the hood. It requires explicit Screen Recording permission granted in System Preferences > Privacy & Security. Attempts to capture without permission return a black frame with no error message.

The **lossless first-pass strategy** works because the capture device delivers frames to ffmpeg's input queue faster than a quality software encoder can consume them. With `-preset ultrafast -crf 0`, the encoder is fast enough to keep up at 1080p30. At 1080p60 or with quality presets, the encoder queue backs up and the capture device's internal buffer overflows, dropping frames. Writing lossless intermediate files (ffv1 is fast and lossless) decouples capture from encoding.

## Sources

- FFmpeg official docs — ffmpeg-devices: https://ffmpeg.org/ffmpeg-devices.html
- GitHub gists — various screen capture examples
- Gumlet Community — "How to record screen with FFmpeg": https://community.gumlet.com/t/how-to-record-screen-with-ffmpeg/518
- ayosec ffmpeg-filters-docs — ddagrab filter documentation: https://github.com/ayosec/ffmpeg-filters-docs

## Learned from Usage

_This section will be populated as agents use this skill and record notable real-world usage patterns, edge cases, and corrections._
