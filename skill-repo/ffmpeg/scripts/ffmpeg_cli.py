"""ffmpeg_cli: Agent-native CLI for ffmpeg.

Calls the real ffmpeg/ffprobe binary — does not process media in Python.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import typer

app = typer.Typer(
    name="ffmpeg-cli",
    help="Agent-native CLI for ffmpeg.",
    no_args_is_help=True,
)

# Command group sub-apps
convert_app = typer.Typer(help="Format conversion, compression, platform encoding")
extract_app = typer.Typer(help="Trim clips, extract audio, frames, sprites")
transform_app = typer.Typer(help="Resize, crop, speed, watermark, subtitles, rotate, fade")
audio_app = typer.Typer(help="Normalize loudness, denoise, remove silence, music ducking")
combine_app = typer.Typer(help="Concatenate, mux, image sequences, compositing")
stream_app = typer.Typer(help="HLS, DASH, multi-bitrate, RTMP, fake live")
util_app = typer.Typer(help="Batch transcode, probe, screen capture, surveillance")

app.add_typer(convert_app, name="convert")
app.add_typer(extract_app, name="extract")
app.add_typer(transform_app, name="transform")
app.add_typer(audio_app, name="audio")
app.add_typer(combine_app, name="combine")
app.add_typer(stream_app, name="stream")
app.add_typer(util_app, name="util")


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

def find_executable(name: str) -> str:
    """Locate ffmpeg or ffprobe, or exit with install instructions."""
    path = shutil.which(name)
    if path is None:
        typer.echo(
            f"ERROR: {name} not found in PATH.\n"
            "Install from: https://ffmpeg.org/download.html\n"
            "  Windows: winget install ffmpeg\n"
            "  macOS:   brew install ffmpeg\n"
            "  Linux:   apt install ffmpeg",
            err=True,
        )
        raise typer.Exit(code=1)
    return path


def detect_version() -> str:
    """Return the ffmpeg version string."""
    exe = find_executable("ffmpeg")
    result = subprocess.run([exe, "-version"], capture_output=True, text=True)
    first_line = result.stdout.split("\n")[0]
    # "ffmpeg version N.N.N ..." or "ffmpeg version N.N.N-ubuntu..."
    parts = first_line.split()
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


def run_ffmpeg(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run an ffmpeg command. Returns CompletedProcess."""
    exe = find_executable("ffmpeg")
    cmd = [exe] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def run_ffprobe(args: list[str]) -> subprocess.CompletedProcess:
    """Run an ffprobe command. Returns CompletedProcess."""
    exe = find_executable("ffprobe")
    cmd = [exe] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_json(input_path: str) -> dict:
    """Run ffprobe and return parsed JSON."""
    result = run_ffprobe([
        "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        input_path,
    ])
    return json.loads(result.stdout)


def get_duration(input_path: str) -> float:
    """Get duration in seconds from ffprobe."""
    data = probe_json(input_path)
    return float(data.get("format", {}).get("duration", 0))


def report_success(output_path: str) -> None:
    """Report successful output with file size."""
    path = Path(output_path)
    if path.exists():
        size = path.stat().st_size
        if size > 1_000_000:
            size_str = f"{size / 1_000_000:.1f} MB"
        elif size > 1_000:
            size_str = f"{size / 1_000:.1f} KB"
        else:
            size_str = f"{size} bytes"
        typer.echo(f"Output: {output_path} ({size_str})")
    else:
        typer.echo(f"Output: {output_path}")


# ---------------------------------------------------------------------------
# convert_app commands
# ---------------------------------------------------------------------------


@convert_app.command("format")
def convert_format(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    codec: str = typer.Option("libx264", help="Video codec"),
    crf: int = typer.Option(23, help="CRF value (lower = higher quality)"),
    preset: str = typer.Option("medium", help="Encoding preset"),
    copy: bool = typer.Option(False, help="Stream copy mode (no re-encoding)"),
) -> None:
    """Convert between formats with optional re-encoding."""
    if copy:
        args = ["-i", input, "-c", "copy", "-movflags", "+faststart", output]
    else:
        args = [
            "-i", input,
            "-c:v", codec, "-crf", str(crf), "-preset", preset,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output,
        ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@convert_app.command("compress")
def convert_compress(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    crf: int = typer.Option(23, help="CRF value"),
    preset: str = typer.Option("medium", help="Encoding preset"),
    target_size: Optional[float] = typer.Option(None, help="Target size in MB (triggers two-pass)"),
) -> None:
    """Compress video with CRF or target-size two-pass."""
    if target_size is not None:
        duration = get_duration(input)
        if duration <= 0:
            typer.echo("ERROR: Could not determine duration", err=True)
            raise typer.Exit(code=1)
        video_bitrate = int((target_size * 8192 / duration) - 128)
        if video_bitrate <= 0:
            typer.echo("ERROR: Target size too small for this duration", err=True)
            raise typer.Exit(code=1)
        # Pass 1
        null_out = "/dev/null" if sys.platform != "win32" else "NUL"
        args1 = [
            "-y", "-i", input,
            "-c:v", "libx264", "-b:v", f"{video_bitrate}k", "-preset", preset,
            "-pass", "1", "-an", "-f", "null", null_out,
        ]
        typer.echo(f"Running: ffmpeg {' '.join(args1)}", err=True)
        run_ffmpeg(args1)
        # Pass 2
        args2 = [
            "-y", "-i", input,
            "-c:v", "libx264", "-b:v", f"{video_bitrate}k", "-preset", preset,
            "-pass", "2", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output,
        ]
        typer.echo(f"Running: ffmpeg {' '.join(args2)}", err=True)
        run_ffmpeg(args2)
    else:
        args = [
            "-i", input,
            "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output,
        ]
        typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
        run_ffmpeg(args)
    report_success(output)


@convert_app.command("audio")
def convert_audio(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    codec: Optional[str] = typer.Option(None, help="Audio codec (auto-detected from extension)"),
    quality: int = typer.Option(2, help="VBR quality for MP3 (0=best, 9=worst)"),
    bitrate: Optional[str] = typer.Option(None, help="CBR bitrate (e.g. 192k), overrides quality"),
) -> None:
    """Extract/convert audio to various formats."""
    ext = Path(output).suffix.lower()
    codec_map = {
        ".mp3": "libmp3lame",
        ".m4a": "aac",
        ".aac": "aac",
        ".ogg": "libvorbis",
        ".flac": "flac",
        ".wav": "pcm_s16le",
    }
    if codec is None:
        codec = codec_map.get(ext, "aac")
    args = ["-i", input, "-vn", "-c:a", codec]
    if bitrate:
        args += ["-b:a", bitrate]
    elif ext == ".mp3":
        args += ["-q:a", str(quality)]
    args.append(output)
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@convert_app.command("platform")
def convert_platform(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    platform: str = typer.Option(..., help="Target platform: youtube, twitter, tiktok"),
) -> None:
    """Encode for a specific platform with optimal settings."""
    platform_settings = {
        "youtube": [
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-pix_fmt", "yuv420p", "-bf", "2", "-g", "30",
            "-c:a", "aac", "-b:a", "384k", "-ar", "48000",
            "-movflags", "+faststart",
        ],
        "twitter": [
            "-c:v", "libx264", "-crf", "23", "-preset", "medium",
            "-pix_fmt", "yuv420p",
            "-vf", "scale='min(1280,iw)':min'(720,ih)':force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-movflags", "+faststart",
        ],
        "tiktok": [
            "-c:v", "libx264", "-crf", "20", "-preset", "medium",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-movflags", "+faststart",
        ],
    }
    settings = platform_settings.get(platform.lower())
    if settings is None:
        typer.echo(f"ERROR: Unknown platform '{platform}'. Use: youtube, twitter, tiktok", err=True)
        raise typer.Exit(code=1)
    args = ["-i", input] + settings + [output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@convert_app.command("to-gif")
def convert_to_gif(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output GIF path"),
    fps: int = typer.Option(15, help="Frames per second"),
    width: int = typer.Option(480, help="Output width in pixels"),
    start: Optional[str] = typer.Option(None, help="Start timestamp (e.g. 00:01:30)"),
    duration: Optional[str] = typer.Option(None, help="Duration (e.g. 5 for 5 seconds)"),
) -> None:
    """Convert video to GIF with palette optimization."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        palette_path = tmp.name
    try:
        time_args: list[str] = []
        if start:
            time_args += ["-ss", start]
        if duration:
            time_args += ["-t", duration]
        filters = f"fps={fps},scale={width}:-1:flags=lanczos"
        # Pass 1: generate palette
        args1 = time_args + [
            "-i", input,
            "-vf", f"{filters},palettegen=stats_mode=diff",
            "-y", palette_path,
        ]
        typer.echo(f"Running: ffmpeg {' '.join(args1)}", err=True)
        run_ffmpeg(args1)
        # Pass 2: encode with palette
        args2 = time_args + [
            "-i", input, "-i", palette_path,
            "-lavfi", f"{filters} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
            "-y", output,
        ]
        typer.echo(f"Running: ffmpeg {' '.join(args2)}", err=True)
        run_ffmpeg(args2)
    finally:
        Path(palette_path).unlink(missing_ok=True)
    report_success(output)


@convert_app.command("hwaccel")
def convert_hwaccel(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    encoder: str = typer.Option(..., help="HW encoder: nvenc, vaapi, videotoolbox"),
    quality: Optional[int] = typer.Option(None, help="Quality value (encoder-specific)"),
    hevc: bool = typer.Option(False, help="Use HEVC instead of H.264"),
) -> None:
    """Encode with hardware acceleration."""
    encoder_map = {
        "nvenc": {
            "h264": "h264_nvenc", "hevc": "hevc_nvenc",
            "quality_flag": "-cq", "default_quality": 23,
        },
        "vaapi": {
            "h264": "h264_vaapi", "hevc": "hevc_vaapi",
            "quality_flag": "-qp", "default_quality": 20,
        },
        "videotoolbox": {
            "h264": "h264_videotoolbox", "hevc": "hevc_videotoolbox",
            "quality_flag": "-q:v", "default_quality": 65,
        },
    }
    enc = encoder_map.get(encoder.lower())
    if enc is None:
        typer.echo(f"ERROR: Unknown encoder '{encoder}'. Use: nvenc, vaapi, videotoolbox", err=True)
        raise typer.Exit(code=1)
    codec_key = "hevc" if hevc else "h264"
    q = quality if quality is not None else enc["default_quality"]
    args = ["-i", input, "-c:v", enc[codec_key], enc["quality_flag"], str(q)]
    if encoder.lower() == "vaapi":
        args = ["-vaapi_device", "/dev/dri/renderD128", "-vf", "format=nv12,hwupload"] + args
    args += ["-c:a", "aac", "-b:a", "128k", output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


# ---------------------------------------------------------------------------
# extract_app commands
# ---------------------------------------------------------------------------


@extract_app.command("clip")
def extract_clip(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    start: str = typer.Option(..., help="Start timestamp (e.g. 00:01:30 or 90)"),
    end: Optional[str] = typer.Option(None, help="End timestamp"),
    duration: Optional[str] = typer.Option(None, help="Duration (e.g. 10 for 10s)"),
    copy: bool = typer.Option(False, help="Stream copy (no re-encoding)"),
) -> None:
    """Extract a clip from a video."""
    args = ["-ss", start, "-i", input]
    if end:
        args += ["-to", end]
    elif duration:
        args += ["-t", duration]
    if copy:
        args += ["-c", "copy", "-avoid_negative_ts", "make_zero"]
    else:
        args += [
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        ]
    args.append(output)
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@extract_app.command("audio")
def extract_audio(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output audio file path"),
    format: Optional[str] = typer.Option(None, help="Audio format (auto from extension)"),
    quality: int = typer.Option(2, help="VBR quality for MP3"),
    bitrate: Optional[str] = typer.Option(None, help="CBR bitrate (e.g. 192k)"),
    track: int = typer.Option(0, help="Audio track index"),
) -> None:
    """Extract audio track from a video."""
    ext = Path(output).suffix.lower()
    codec_map = {
        ".mp3": "libmp3lame",
        ".m4a": "aac",
        ".aac": "aac",
        ".ogg": "libvorbis",
        ".flac": "flac",
        ".wav": "pcm_s16le",
    }
    codec = codec_map.get(ext, "aac")
    args = ["-i", input, "-vn", "-map", f"0:a:{track}", "-c:a", codec]
    if bitrate:
        args += ["-b:a", bitrate]
    elif ext == ".mp3":
        args += ["-q:a", str(quality)]
    args.append(output)
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@extract_app.command("frames")
def extract_frames(
    input: str = typer.Argument(..., help="Input file path"),
    output_pattern: str = typer.Option("frame_%04d.jpg", help="Output filename pattern"),
    at: Optional[str] = typer.Option(None, help="Extract single frame at timestamp"),
    every: Optional[float] = typer.Option(None, help="Extract frame every N seconds"),
    iframes: bool = typer.Option(False, help="Extract only I-frames"),
    width: Optional[int] = typer.Option(None, help="Scale width (height auto)"),
) -> None:
    """Extract frames from a video."""
    if at:
        args = ["-ss", at, "-i", input]
        filters: list[str] = []
        if width:
            filters.append(f"scale={width}:-2")
        if filters:
            args += ["-vf", ",".join(filters)]
        args += ["-frames:v", "1", output_pattern]
    elif every:
        args = ["-i", input]
        filters = [f"fps=1/{every}"]
        if width:
            filters.append(f"scale={width}:-2")
        args += ["-vf", ",".join(filters), output_pattern]
    elif iframes:
        args = ["-i", input]
        filters = ["select='eq(pict_type,I)'"]
        if width:
            filters.append(f"scale={width}:-2")
        args += ["-vf", ",".join(filters), "-vsync", "vfr", output_pattern]
    else:
        args = ["-i", input]
        if width:
            args += ["-vf", f"scale={width}:-2"]
        args += [output_pattern]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    typer.echo(f"Frames extracted to pattern: {output_pattern}")


@extract_app.command("sprite")
def extract_sprite(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output sprite sheet path"),
    cols: int = typer.Option(10, help="Number of columns"),
    rows: int = typer.Option(10, help="Number of rows"),
    thumb_width: int = typer.Option(160, help="Thumbnail width in pixels"),
) -> None:
    """Generate a sprite sheet / thumbnail grid."""
    duration = get_duration(input)
    total = cols * rows
    if duration <= 0:
        typer.echo("ERROR: Could not determine duration", err=True)
        raise typer.Exit(code=1)
    interval = duration / total
    vf = f"fps=1/{interval},scale={thumb_width}:-1,tile={cols}x{rows}"
    args = ["-i", input, "-vf", vf, "-frames:v", "1", output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


# ---------------------------------------------------------------------------
# transform_app commands
# ---------------------------------------------------------------------------


@transform_app.command("resize")
def transform_resize(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    width: Optional[int] = typer.Option(None, help="Target width"),
    height: Optional[int] = typer.Option(None, help="Target height"),
    letterbox: bool = typer.Option(False, help="Letterbox to exact dimensions"),
) -> None:
    """Resize video."""
    if width is None and height is None:
        typer.echo("ERROR: Provide at least --width or --height", err=True)
        raise typer.Exit(code=1)
    w = str(width) if width else "-2"
    h = str(height) if height else "-2"
    if letterbox and width and height:
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        )
    else:
        vf = f"scale={w}:{h}"
    args = [
        "-i", input, "-vf", vf,
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", output,
    ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@transform_app.command("crop")
def transform_crop(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    aspect: str = typer.Option("9:16", help="Target aspect ratio (e.g. 9:16)"),
    pad: bool = typer.Option(False, help="Pad instead of crop"),
) -> None:
    """Crop or pad to a target aspect ratio."""
    parts = aspect.split(":")
    aw, ah = int(parts[0]), int(parts[1])
    if pad:
        vf = (
            f"scale=iw:ih:force_original_aspect_ratio=decrease,"
            f"pad=ih*{aw}/{ah}:ih:(ow-iw)/2:(oh-ih)/2"
        )
    else:
        vf = f"crop=ih*{aw}/{ah}:ih"
    args = [
        "-i", input, "-vf", vf,
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", output,
    ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@transform_app.command("speed")
def transform_speed(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    factor: float = typer.Option(..., help="Speed factor (2.0 = 2x fast, 0.5 = slow-mo)"),
    interpolate: bool = typer.Option(False, help="Use minterpolate for smooth slow-mo"),
    no_audio: bool = typer.Option(False, help="Discard audio"),
) -> None:
    """Change playback speed."""
    pts_factor = 1.0 / factor
    video_filter = f"setpts={pts_factor}*PTS"
    if interpolate and factor < 1.0:
        target_fps = 60
        video_filter = f"setpts={pts_factor}*PTS,minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"

    if no_audio:
        args = ["-i", input, "-vf", video_filter, "-an", output]
    else:
        # Build atempo chain (atempo only accepts 0.5-2.0 range)
        atempo_parts: list[str] = []
        remaining = factor
        if remaining > 1.0:
            while remaining > 2.0:
                atempo_parts.append("atempo=2.0")
                remaining /= 2.0
            atempo_parts.append(f"atempo={remaining}")
        elif remaining < 1.0:
            while remaining < 0.5:
                atempo_parts.append("atempo=0.5")
                remaining /= 0.5
            atempo_parts.append(f"atempo={remaining}")
        else:
            atempo_parts.append("atempo=1.0")
        af = ",".join(atempo_parts)
        args = ["-i", input, "-vf", video_filter, "-af", af, output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@transform_app.command("watermark")
def transform_watermark(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    logo: str = typer.Option(..., help="Path to watermark PNG"),
    position: str = typer.Option("br", help="Position: tl, tr, bl, br, center"),
    opacity: Optional[float] = typer.Option(None, help="Opacity 0.0-1.0"),
    scale: Optional[int] = typer.Option(None, help="Logo width in pixels"),
) -> None:
    """Add watermark/logo overlay."""
    pos_map = {
        "tl": "10:10",
        "tr": "W-w-10:10",
        "bl": "10:H-h-10",
        "br": "W-w-10:H-h-10",
        "center": "(W-w)/2:(H-h)/2",
    }
    overlay_pos = pos_map.get(position, pos_map["br"])
    filter_parts: list[str] = []
    logo_label = "[1:v]"
    if scale:
        filter_parts.append(f"[1:v]scale={scale}:-1[logo]")
        logo_label = "[logo]"
    if opacity is not None:
        src = logo_label.strip("[]")
        filter_parts.append(f"{logo_label}colorchannelmixer=aa={opacity}[wm]")
        logo_label = "[wm]"
    filter_parts.append(f"[0:v]{logo_label}overlay={overlay_pos}")
    fc = ";".join(filter_parts)
    args = ["-i", input, "-i", logo, "-filter_complex", fc, "-c:a", "copy", output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@transform_app.command("subtitles")
def transform_subtitles(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    srt: str = typer.Option(..., help="Path to SRT/ASS subtitle file"),
    font_size: Optional[int] = typer.Option(None, help="Font size"),
    font_name: Optional[str] = typer.Option(None, help="Font name"),
) -> None:
    """Burn subtitles into video."""
    # Escape special chars in path for ffmpeg filter
    srt_escaped = srt.replace("\\", "/").replace(":", "\\:")
    style_parts: list[str] = []
    if font_size:
        style_parts.append(f"FontSize={font_size}")
    if font_name:
        style_parts.append(f"FontName={font_name}")
    if style_parts:
        style = ",".join(style_parts)
        vf = f"subtitles='{srt_escaped}':force_style='{style}'"
    else:
        vf = f"subtitles='{srt_escaped}'"
    args = ["-i", input, "-vf", vf, "-c:a", "copy", output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@transform_app.command("rotate")
def transform_rotate(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    angle: Optional[int] = typer.Option(None, help="Rotation angle: 90, 180, 270"),
    flip: Optional[str] = typer.Option(None, help="Flip: h (horizontal), v (vertical)"),
) -> None:
    """Rotate or flip video."""
    filters: list[str] = []
    if angle == 90:
        filters.append("transpose=1")
    elif angle == 180:
        filters.append("transpose=1,transpose=1")
    elif angle == 270:
        filters.append("transpose=2")
    elif angle is not None:
        typer.echo("ERROR: --angle must be 90, 180, or 270", err=True)
        raise typer.Exit(code=1)
    if flip == "h":
        filters.append("hflip")
    elif flip == "v":
        filters.append("vflip")
    elif flip is not None:
        typer.echo("ERROR: --flip must be h or v", err=True)
        raise typer.Exit(code=1)
    if not filters:
        typer.echo("ERROR: Provide --angle and/or --flip", err=True)
        raise typer.Exit(code=1)
    vf = ",".join(filters)
    args = ["-i", input, "-vf", vf, "-c:a", "copy", output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@transform_app.command("fade")
def transform_fade(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    fade_in: Optional[float] = typer.Option(None, help="Fade in duration in seconds"),
    fade_out: Optional[float] = typer.Option(None, help="Fade out duration in seconds"),
) -> None:
    """Add fade in/out effects."""
    if fade_in is None and fade_out is None:
        typer.echo("ERROR: Provide --fade-in and/or --fade-out", err=True)
        raise typer.Exit(code=1)
    duration = get_duration(input)
    vf_parts: list[str] = []
    af_parts: list[str] = []
    if fade_in is not None:
        vf_parts.append(f"fade=t=in:st=0:d={fade_in}")
        af_parts.append(f"afade=t=in:st=0:d={fade_in}")
    if fade_out is not None:
        start = max(0, duration - fade_out)
        vf_parts.append(f"fade=t=out:st={start}:d={fade_out}")
        af_parts.append(f"afade=t=out:st={start}:d={fade_out}")
    args = ["-i", input]
    if vf_parts:
        args += ["-vf", ",".join(vf_parts)]
    if af_parts:
        args += ["-af", ",".join(af_parts)]
    args += ["-c:v", "libx264", "-crf", "18", "-preset", "medium", output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


# ---------------------------------------------------------------------------
# audio_app commands
# ---------------------------------------------------------------------------


@audio_app.command("normalize")
def audio_normalize(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    target: float = typer.Option(-16, help="Target loudness in LUFS"),
    tp: float = typer.Option(-1.5, help="True peak in dBTP"),
) -> None:
    """Normalize audio loudness (EBU R128 two-pass)."""
    null_out = "/dev/null" if sys.platform != "win32" else "NUL"
    # Pass 1: measure
    af1 = f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json"
    args1 = ["-i", input, "-af", af1, "-f", "null", null_out]
    typer.echo(f"Running: ffmpeg {' '.join(args1)}", err=True)
    result = run_ffmpeg(args1, check=False)
    # Parse JSON from stderr (last 12 lines)
    lines = result.stderr.strip().split("\n")
    json_str = ""
    brace_count = 0
    json_lines: list[str] = []
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.endswith("}"):
            brace_count += 1
        if brace_count > 0:
            json_lines.insert(0, stripped)
        if stripped.startswith("{"):
            brace_count -= 1
            if brace_count == 0:
                break
    json_str = "\n".join(json_lines)
    try:
        measured = json.loads(json_str)
    except json.JSONDecodeError:
        typer.echo("ERROR: Could not parse loudnorm measurements from ffmpeg output", err=True)
        raise typer.Exit(code=1)
    mi = measured["input_i"]
    mtp = measured["input_tp"]
    mlra = measured["input_lra"]
    mt = measured["input_thresh"]
    # Pass 2: apply
    af2 = (
        f"loudnorm=I={target}:TP={tp}:LRA=11:"
        f"measured_I={mi}:measured_TP={mtp}:measured_LRA={mlra}:"
        f"measured_thresh={mt}:linear=true"
    )
    args2 = ["-i", input, "-af", af2, "-ar", "48000", output]
    typer.echo(f"Running: ffmpeg {' '.join(args2)}", err=True)
    run_ffmpeg(args2)
    report_success(output)


@audio_app.command("silence")
def audio_silence(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    threshold: str = typer.Option("-35dB", help="Silence threshold"),
    min_duration: float = typer.Option(1.0, help="Minimum silence duration in seconds"),
    keep_padding: float = typer.Option(0.3, help="Seconds of silence to keep"),
) -> None:
    """Remove silence from audio/video."""
    af = (
        f"silenceremove=stop_periods=-1:stop_duration={min_duration}:"
        f"stop_threshold={threshold}:stop_silence={keep_padding}"
    )
    args = ["-i", input, "-af", af, output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@audio_app.command("denoise")
def audio_denoise(
    input: str = typer.Argument(..., help="Input file path"),
    output: str = typer.Argument(..., help="Output file path"),
    method: str = typer.Option("fft", help="Method: fft or rnn"),
    strength: Optional[float] = typer.Option(None, help="Strength (fft: 0-97 default 12, rnn: 0-1 default 0.8)"),
    model: Optional[str] = typer.Option(None, help="Path to .rnnn model file (for rnn method)"),
) -> None:
    """Reduce background noise."""
    if method == "fft":
        s = strength if strength is not None else 12
        af = f"afftdn=nr={s}:nf=-45:tn=1"
    elif method == "rnn":
        s = strength if strength is not None else 0.8
        if model is None:
            typer.echo("ERROR: --model is required for rnn method (path to .rnnn file)", err=True)
            raise typer.Exit(code=1)
        af = f"arnndn=m={model}:mix={s}"
    else:
        typer.echo("ERROR: --method must be fft or rnn", err=True)
        raise typer.Exit(code=1)
    args = ["-i", input, "-af", af, output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@audio_app.command("duck")
def audio_duck(
    output: str = typer.Argument(..., help="Output file path"),
    voice: str = typer.Option(..., help="Voice/dialogue track path"),
    music: str = typer.Option(..., help="Music/background track path"),
    music_level: float = typer.Option(0.15, help="Music volume when voice is present (0.0-1.0)"),
    dynamic: bool = typer.Option(False, help="Use sidechaincompress for dynamic ducking"),
) -> None:
    """Duck music under voice/dialogue."""
    if dynamic:
        fc = (
            f"[1:a]asplit=2[sc][music];[0:a][sc]sidechaincompress="
            f"threshold=0.015:ratio=10:attack=200:release=1000[voice];"
            f"[voice][music]amix=inputs=2:duration=longest:normalize=0"
        )
    else:
        fc = (
            f"[1:a]volume={music_level}[music];"
            f"[0:a][music]amix=inputs=2:duration=longest:normalize=0"
        )
    args = ["-i", voice, "-i", music, "-filter_complex", fc, output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


# ---------------------------------------------------------------------------
# combine_app commands
# ---------------------------------------------------------------------------


@combine_app.command("concat")
def combine_concat(
    output: str = typer.Argument(..., help="Output file path"),
    files: List[str] = typer.Option(..., help="Input files to concatenate"),
    filter: bool = typer.Option(False, "--filter", help="Use concat filter (for mismatched formats)"),
) -> None:
    """Concatenate multiple files."""
    if filter:
        inputs: list[str] = []
        filter_inputs = ""
        for i, f in enumerate(files):
            inputs += ["-i", f]
            filter_inputs += f"[{i}:v:0][{i}:a:0]"
        fc = f"{filter_inputs}concat=n={len(files)}:v=1:a=1[outv][outa]"
        args = inputs + ["-filter_complex", fc, "-map", "[outv]", "-map", "[outa]", output]
    else:
        # Demuxer mode: write temp filelist
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            for f in files:
                abs_path = str(Path(f).resolve()).replace("\\", "/")
                tmp.write(f"file '{abs_path}'\n")
            filelist = tmp.name
        try:
            args = ["-f", "concat", "-safe", "0", "-i", filelist, "-c", "copy", output]
            typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
            run_ffmpeg(args)
        finally:
            Path(filelist).unlink(missing_ok=True)
        report_success(output)
        return
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@combine_app.command("mux")
def combine_mux(
    output: str = typer.Argument(..., help="Output file path"),
    video: str = typer.Option(..., help="Video file path"),
    audio: str = typer.Option(..., help="Audio file path"),
    delay: Optional[float] = typer.Option(None, help="Audio delay in seconds"),
) -> None:
    """Mux video and audio tracks together."""
    args: list[str] = []
    if delay:
        args += ["-itsoffset", str(delay)]
    args += ["-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", output]
    # If delay was set, -itsoffset applies to the next -i, so reorder
    if delay:
        args = ["-i", video, "-itsoffset", str(delay), "-i", audio,
                "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", output]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@combine_app.command("from-images")
def combine_from_images(
    output: str = typer.Argument(..., help="Output file path"),
    pattern: str = typer.Option(..., help="Image pattern (e.g. frame_%04d.png)"),
    framerate: int = typer.Option(24, help="Input framerate"),
    codec: str = typer.Option("libx264", help="Video codec"),
    crf: int = typer.Option(20, help="CRF value"),
) -> None:
    """Create video from image sequence."""
    args = [
        "-framerate", str(framerate),
        "-i", pattern,
        "-c:v", codec, "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        output,
    ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@combine_app.command("composite")
def combine_composite(
    output: str = typer.Argument(..., help="Output file path"),
    inputs: List[str] = typer.Option(..., help="Input file paths"),
    layout: str = typer.Option(..., help="Layout: pip, side-by-side, grid"),
) -> None:
    """Composite multiple videos into one frame."""
    input_args: list[str] = []
    for f in inputs:
        input_args += ["-i", f]
    if layout == "pip":
        # Main video full size, second video small in bottom-right
        fc = "[1:v]scale=iw/4:-1[pip];[0:v][pip]overlay=W-w-10:H-h-10"
        args = input_args + ["-filter_complex", fc, "-c:a", "copy", output]
    elif layout == "side-by-side":
        fc = "[0:v]scale=iw/2:ih/2[left];[1:v]scale=iw/2:ih/2[right];[left][right]hstack=inputs=2"
        args = input_args + ["-filter_complex", fc, "-c:a", "copy", output]
    elif layout == "grid":
        n = len(inputs)
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        parts: list[str] = []
        for i in range(n):
            parts.append(f"[{i}:v]scale=iw/{cols}:ih/{rows}[v{i}]")
        # Build rows
        row_labels: list[str] = []
        for r in range(rows):
            row_inputs = ""
            count = 0
            for c in range(cols):
                idx = r * cols + c
                if idx < n:
                    row_inputs += f"[v{idx}]"
                    count += 1
            if count > 1:
                parts.append(f"{row_inputs}hstack=inputs={count}[row{r}]")
                row_labels.append(f"[row{r}]")
            elif count == 1:
                row_labels.append(row_inputs)
        if len(row_labels) > 1:
            parts.append(f"{''.join(row_labels)}vstack=inputs={len(row_labels)}")
        fc = ";".join(parts)
        args = input_args + ["-filter_complex", fc, output]
    else:
        typer.echo("ERROR: --layout must be pip, side-by-side, or grid", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


# ---------------------------------------------------------------------------
# stream_app commands
# ---------------------------------------------------------------------------

QUALITY_PRESETS = {
    "1080p": {"scale": "1920:1080", "bitrate": "5000k", "maxrate": "5350k", "bufsize": "7500k"},
    "720p": {"scale": "1280:720", "bitrate": "2800k", "maxrate": "2996k", "bufsize": "4200k"},
    "480p": {"scale": "854:480", "bitrate": "1400k", "maxrate": "1498k", "bufsize": "2100k"},
    "360p": {"scale": "640:360", "bitrate": "800k", "maxrate": "856k", "bufsize": "1200k"},
}


def _parse_qualities(qualities_str: str) -> list[str]:
    return [q.strip() for q in qualities_str.split(",")]


@stream_app.command("hls")
def stream_hls(
    input: str = typer.Argument(..., help="Input file path"),
    output_dir: str = typer.Option(..., help="Output directory"),
    segment_duration: int = typer.Option(6, help="Segment duration in seconds"),
    qualities: str = typer.Option("1080p,720p,480p", help="Comma-separated quality list"),
) -> None:
    """Generate multi-quality HLS output."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    qs = _parse_qualities(qualities)
    args = ["-i", input]
    filter_parts: list[str] = []
    # Split input for each quality
    split_out = "".join(f"[v{i}]" for i in range(len(qs)))
    filter_parts.append(f"[0:v]split={len(qs)}{split_out}")
    for i, q in enumerate(qs):
        preset = QUALITY_PRESETS.get(q, QUALITY_PRESETS["720p"])
        filter_parts.append(f"[v{i}]scale={preset['scale']}[v{i}out]")
    args += ["-filter_complex", ";".join(filter_parts)]
    for i, q in enumerate(qs):
        preset = QUALITY_PRESETS.get(q, QUALITY_PRESETS["720p"])
        args += [
            "-map", f"[v{i}out]", "-map", "0:a",
            f"-c:v:{i}", "libx264", f"-b:v:{i}", preset["bitrate"],
            f"-maxrate:{i}", preset["maxrate"], f"-bufsize:{i}", preset["bufsize"],
            f"-c:a:{i}", "aac", f"-b:a:{i}", "128k",
        ]
    var_stream_map = " ".join(f"v:{i},a:{i},name:{q}" for i, q in enumerate(qs))
    master_pl = str(Path(output_dir) / "master.m3u8")
    args += [
        "-f", "hls",
        "-hls_time", str(segment_duration),
        "-hls_playlist_type", "vod",
        "-hls_flags", "independent_segments",
        "-sc_threshold", "0",
        "-var_stream_map", var_stream_map,
        "-master_pl_name", "master.m3u8",
        str(Path(output_dir) / "%v/stream.m3u8"),
    ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    typer.echo(f"HLS output: {output_dir}")


@stream_app.command("dash")
def stream_dash(
    input: str = typer.Argument(..., help="Input file path"),
    output_dir: str = typer.Option(..., help="Output directory"),
    segment_duration: int = typer.Option(4, help="Segment duration in seconds"),
    qualities: str = typer.Option("1080p,720p,480p", help="Comma-separated quality list"),
) -> None:
    """Generate DASH output with multiple quality levels."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    qs = _parse_qualities(qualities)
    args = ["-i", input]
    filter_parts: list[str] = []
    split_out = "".join(f"[v{i}]" for i in range(len(qs)))
    filter_parts.append(f"[0:v]split={len(qs)}{split_out}")
    for i, q in enumerate(qs):
        preset = QUALITY_PRESETS.get(q, QUALITY_PRESETS["720p"])
        filter_parts.append(f"[v{i}]scale={preset['scale']}[v{i}out]")
    args += ["-filter_complex", ";".join(filter_parts)]
    for i, q in enumerate(qs):
        preset = QUALITY_PRESETS.get(q, QUALITY_PRESETS["720p"])
        args += [
            "-map", f"[v{i}out]",
            f"-c:v:{i}", "libx264", f"-b:v:{i}", preset["bitrate"],
            f"-maxrate:{i}", preset["maxrate"], f"-bufsize:{i}", preset["bufsize"],
        ]
    args += ["-map", "0:a", "-c:a", "aac", "-b:a", "128k"]
    adaptation_sets = "id=0,streams=v id=1,streams=a"
    manifest = str(Path(output_dir) / "manifest.mpd")
    args += [
        "-f", "dash",
        "-seg_duration", str(segment_duration),
        "-adaptation_sets", adaptation_sets,
        "-use_template", "1",
        "-use_timeline", "1",
        manifest,
    ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    typer.echo(f"DASH output: {output_dir}")


@stream_app.command("ladder")
def stream_ladder(
    input: str = typer.Argument(..., help="Input file path"),
    output_dir: str = typer.Option(..., help="Output directory"),
    qualities: str = typer.Option("1080p,720p,480p", help="Comma-separated quality list"),
) -> None:
    """Encode multiple quality levels to separate MP4 files."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    qs = _parse_qualities(qualities)
    args = ["-i", input]
    filter_parts: list[str] = []
    split_out = "".join(f"[v{i}]" for i in range(len(qs)))
    filter_parts.append(f"[0:v]split={len(qs)}{split_out}")
    for i, q in enumerate(qs):
        preset = QUALITY_PRESETS.get(q, QUALITY_PRESETS["720p"])
        filter_parts.append(f"[v{i}]scale={preset['scale']}[v{i}out]")
    args += ["-filter_complex", ";".join(filter_parts)]
    for i, q in enumerate(qs):
        preset = QUALITY_PRESETS.get(q, QUALITY_PRESETS["720p"])
        out_path = str(Path(output_dir) / f"{q}.mp4")
        args += [
            "-map", f"[v{i}out]", "-map", "0:a",
            f"-c:v:{i}", "libx264", f"-b:v:{i}", preset["bitrate"],
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
        ]
    # For separate files, we need to run per quality
    # Rewrite: run one command per quality instead
    typer.echo("Encoding quality ladder...", err=True)
    for q in qs:
        preset = QUALITY_PRESETS.get(q, QUALITY_PRESETS["720p"])
        out_path = str(Path(output_dir) / f"{q}.mp4")
        single_args = [
            "-i", input,
            "-vf", f"scale={preset['scale']}",
            "-c:v", "libx264", "-b:v", preset["bitrate"],
            "-maxrate", preset["maxrate"], "-bufsize", preset["bufsize"],
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ]
        typer.echo(f"Running: ffmpeg {' '.join(single_args)}", err=True)
        run_ffmpeg(single_args)
        report_success(out_path)


@stream_app.command("restream")
def stream_restream(
    input: str = typer.Argument(..., help="Input file or stream URL"),
    destinations: List[str] = typer.Option(..., help="RTMP destination URLs"),
) -> None:
    """Re-stream to multiple RTMP destinations."""
    tee_parts = "|".join(f"[f=flv:onfail=ignore]{url}" for url in destinations)
    args = [
        "-re", "-i", input,
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "tee", "-map", "0:v", "-map", "0:a",
        tee_parts,
    ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)


@stream_app.command("fake-live")
def stream_fake_live(
    input: str = typer.Argument(..., help="Input file path"),
    url: str = typer.Option(..., help="RTMP destination URL"),
    loop: bool = typer.Option(False, help="Loop the input"),
    playlist: Optional[str] = typer.Option(None, help="Path to filelist.txt for playlist mode"),
) -> None:
    """Stream a file as fake live to RTMP."""
    args: list[str] = ["-re"]
    if loop and playlist is None:
        args += ["-stream_loop", "-1"]
    if playlist:
        args += ["-f", "concat", "-safe", "0", "-i", playlist]
    else:
        args += ["-i", input]
    args += [
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "flv", url,
    ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)


# ---------------------------------------------------------------------------
# util_app commands
# ---------------------------------------------------------------------------


@util_app.command("batch")
def util_batch(
    input_dir: str = typer.Option(..., help="Input directory"),
    output_dir: str = typer.Option(..., help="Output directory"),
    format: str = typer.Option("mp4", help="Output format/extension"),
    crf: int = typer.Option(23, help="CRF value"),
    preset: str = typer.Option("medium", help="Encoding preset"),
) -> None:
    """Batch transcode all videos in a directory."""
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    video_exts = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".ts"}
    count = 0
    for f in sorted(in_path.iterdir()):
        if f.suffix.lower() not in video_exts:
            continue
        output_file = out_path / f"{f.stem}.{format}"
        if output_file.exists():
            typer.echo(f"Skipping (exists): {output_file}", err=True)
            continue
        args = [
            "-i", str(f),
            "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_file),
        ]
        typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
        run_ffmpeg(args)
        report_success(str(output_file))
        count += 1
    typer.echo(f"Batch complete: {count} files processed")


@util_app.command("probe")
def util_probe(
    input: str = typer.Argument(..., help="Input file path"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Probe media file and display info."""
    data = probe_json(input)
    if json_output:
        typer.echo(json.dumps(data, indent=2))
        return
    from rich.console import Console
    from rich.table import Table
    console = Console()
    # Format info
    fmt = data.get("format", {})
    fmt_table = Table(title=f"File: {Path(input).name}")
    fmt_table.add_column("Property", style="cyan")
    fmt_table.add_column("Value", style="green")
    fmt_table.add_row("Format", fmt.get("format_long_name", fmt.get("format_name", "unknown")))
    dur = float(fmt.get("duration", 0))
    hours, remainder = divmod(int(dur), 3600)
    minutes, seconds = divmod(remainder, 60)
    fmt_table.add_row("Duration", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    size = int(fmt.get("size", 0))
    fmt_table.add_row("Size", f"{size / 1_000_000:.1f} MB" if size > 0 else "unknown")
    bitrate = int(fmt.get("bit_rate", 0))
    fmt_table.add_row("Bitrate", f"{bitrate / 1000:.0f} kbps" if bitrate > 0 else "unknown")
    console.print(fmt_table)
    # Streams
    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type", "unknown")
        st = Table(title=f"Stream #{stream.get('index', '?')} ({codec_type})")
        st.add_column("Property", style="cyan")
        st.add_column("Value", style="green")
        st.add_row("Codec", stream.get("codec_long_name", stream.get("codec_name", "unknown")))
        if codec_type == "video":
            st.add_row("Resolution", f"{stream.get('width', '?')}x{stream.get('height', '?')}")
            st.add_row("FPS", str(stream.get("r_frame_rate", "unknown")))
            st.add_row("Pixel Format", str(stream.get("pix_fmt", "unknown")))
        elif codec_type == "audio":
            st.add_row("Sample Rate", f"{stream.get('sample_rate', '?')} Hz")
            st.add_row("Channels", str(stream.get("channels", "?")))
            st.add_row("Channel Layout", str(stream.get("channel_layout", "unknown")))
        console.print(st)


@util_app.command("record")
def util_record(
    output: str = typer.Option(..., help="Output file path"),
    fps: int = typer.Option(30, help="Frames per second"),
    audio: bool = typer.Option(False, help="Record audio too"),
) -> None:
    """Record screen (platform-detected input device)."""
    if sys.platform == "win32":
        input_format = "gdigrab"
        input_device = "desktop"
        audio_args = ["-f", "dshow", "-i", "audio=virtual-audio-capturer"] if audio else []
    elif sys.platform == "darwin":
        input_format = "avfoundation"
        input_device = "1:0" if audio else "1:none"
        audio_args = []
    else:
        input_format = "x11grab"
        input_device = os.environ.get("DISPLAY", ":0.0")
        audio_args = ["-f", "pulse", "-i", "default"] if audio else []
    args = ["-f", input_format, "-framerate", str(fps), "-i", input_device]
    args += audio_args
    args += [
        "-c:v", "libx264", "-crf", "20", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        output,
    ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)
    report_success(output)


@util_app.command("surveillance")
def util_surveillance(
    url: str = typer.Option(..., help="RTSP stream URL"),
    output_dir: str = typer.Option(..., help="Output directory for segments"),
    segment_time: int = typer.Option(900, help="Segment duration in seconds"),
) -> None:
    """Record RTSP stream with segmented output."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_pattern = str(Path(output_dir) / "%Y-%m-%d_%H-%M-%S.mp4")
    args = [
        "-rtsp_transport", "tcp",
        "-use_wallclock_as_timestamps", "1",
        "-i", url,
        "-c", "copy",
        "-f", "segment",
        "-segment_time", str(segment_time),
        "-strftime", "1",
        "-reset_timestamps", "1",
        output_pattern,
    ]
    typer.echo(f"Running: ffmpeg {' '.join(args)}", err=True)
    run_ffmpeg(args)


if __name__ == "__main__":
    app()
