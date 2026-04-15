"""Tier 2 integration tests for the ffmpeg skill CLI.

These tests run real ffmpeg commands and verify output files.
Requires ffmpeg 7.x installed in PATH.

Marker: integration
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup -- skill lives outside the qa/ tree
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skill-repo" / "ffmpeg" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_QA_DIR = Path(__file__).parent.parent
if str(_QA_DIR) not in sys.path:
    sys.path.insert(0, str(_QA_DIR))

from typer.testing import CliRunner

from ffmpeg_cli import app  # noqa: E402

# Import helpers from conftest (module-level functions)
from conftest import (  # noqa: E402
    assert_audio_properties,
    assert_duration_approx,
    assert_file_exists_and_nonzero,
    assert_video_properties,
    probe_format,
)

runner = CliRunner()


# ===========================================================================
# convert group
# ===========================================================================


@pytest.mark.integration
def test_convert_format_reencode(test_video, tmp_path, ffprobe_path):
    """convert format -- re-encode to H.264 MP4 with default CRF."""
    output = tmp_path / "output.mp4"
    result = runner.invoke(app, ["convert", "format", str(test_video), str(output)])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]

    # Verify H.264 video
    assert len(video_streams) > 0, "No video stream in output"
    assert video_streams[0]["codec_name"] == "h264", f"Expected h264, got {video_streams[0]['codec_name']}"

    # Verify AAC audio
    assert len(audio_streams) > 0, "No audio stream in output"
    assert audio_streams[0]["codec_name"] == "aac", f"Expected aac audio, got {audio_streams[0]['codec_name']}"

    # Verify yuv420p pixel format
    assert video_streams[0].get("pix_fmt") == "yuv420p", (
        f"Expected yuv420p pixel format, got {video_streams[0].get('pix_fmt')}"
    )

    # Verify duration matches input (~3 seconds)
    assert_duration_approx(ffprobe_path, output, expected_seconds=3.0, tolerance=0.5)


@pytest.mark.integration
def test_convert_format_copy(test_video, tmp_path, ffprobe_path):
    """convert format --copy -- transmux without re-encoding."""
    output = tmp_path / "output.mkv"
    result = runner.invoke(app, ["convert", "format", str(test_video), str(output), "--copy"])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    # Probe source and output
    src_data = probe_format(ffprobe_path, test_video)
    out_data = probe_format(ffprobe_path, output)

    src_video = [s for s in src_data.get("streams", []) if s.get("codec_type") == "video"]
    out_video = [s for s in out_data.get("streams", []) if s.get("codec_type") == "video"]
    src_audio = [s for s in src_data.get("streams", []) if s.get("codec_type") == "audio"]
    out_audio = [s for s in out_data.get("streams", []) if s.get("codec_type") == "audio"]

    # Stream copy should preserve codecs exactly
    assert len(out_video) > 0, "No video stream in output"
    assert out_video[0]["codec_name"] == src_video[0]["codec_name"], (
        f"Video codec mismatch: source={src_video[0]['codec_name']}, output={out_video[0]['codec_name']}"
    )
    assert len(out_audio) > 0, "No audio stream in output"
    assert out_audio[0]["codec_name"] == src_audio[0]["codec_name"], (
        f"Audio codec mismatch: source={src_audio[0]['codec_name']}, output={out_audio[0]['codec_name']}"
    )


@pytest.mark.integration
def test_convert_compress_crf(test_video, tmp_path, ffprobe_path):
    """convert compress -- CRF compression should produce smaller file than high-quality source."""
    output = tmp_path / "compressed.mp4"
    # Use a high CRF (lower quality, smaller file) vs the source at CRF 28
    result = runner.invoke(app, [
        "convert", "compress", str(test_video), str(output),
        "--crf", "40", "--preset", "ultrafast",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    # Verify output is smaller than input
    assert output.stat().st_size < test_video.stat().st_size, (
        f"Compressed ({output.stat().st_size}) should be smaller than source ({test_video.stat().st_size})"
    )

    # Verify still H.264 with audio
    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    assert len(video_streams) > 0, "No video stream in compressed output"
    assert video_streams[0]["codec_name"] == "h264", f"Expected h264, got {video_streams[0]['codec_name']}"
    assert len(audio_streams) > 0, "No audio stream in compressed output"


@pytest.mark.integration
def test_convert_audio(test_audio, tmp_path, ffprobe_path):
    """convert audio -- WAV to MP3."""
    output = tmp_path / "output.mp3"
    result = runner.invoke(app, ["convert", "audio", str(test_audio), str(output)])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)
    assert_audio_properties(ffprobe_path, output, codec="mp3")

    # Verify MP3 magic bytes: starts with 0xFF 0xFB, 0xFF 0xF3, or "ID3" tag
    with open(output, "rb") as f:
        header = f.read(3)
    is_mp3_sync = (len(header) >= 2 and header[0] == 0xFF and header[1] in (0xFB, 0xF3, 0xE2, 0xE3))
    is_id3 = header == b"ID3"
    assert is_mp3_sync or is_id3, f"Not a valid MP3 file. First 3 bytes: {header.hex()}"

    # Verify duration approximately matches source (~3 seconds)
    assert_duration_approx(ffprobe_path, output, expected_seconds=3.0, tolerance=0.5)


@pytest.mark.integration
def test_convert_to_gif(test_video, tmp_path):
    """convert to-gif -- produce a GIF with correct magic bytes."""
    output = tmp_path / "output.gif"
    result = runner.invoke(app, ["convert", "to-gif", str(test_video), str(output)])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    # GIF magic bytes: GIF87a or GIF89a
    with open(output, "rb") as f:
        magic = f.read(6)
    assert magic in (b"GIF87a", b"GIF89a"), f"Not a valid GIF. Magic bytes: {magic!r}"

    # A 3-second GIF with multiple frames should be > 10KB
    file_size = output.stat().st_size
    assert file_size > 10 * 1024, (
        f"GIF is suspiciously small ({file_size} bytes) for a 3-second source -- likely has few/no frames"
    )


# ===========================================================================
# extract group
# ===========================================================================


@pytest.mark.integration
def test_extract_clip(test_video, tmp_path, ffprobe_path):
    """extract clip -- trim first 1 second, verify duration ~1s."""
    output = tmp_path / "clip.mp4"
    result = runner.invoke(app, [
        "extract", "clip", str(test_video), str(output),
        "--start", "0", "--duration", "1",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    # Verify duration is approximately 1 second (tight tolerance)
    assert_duration_approx(ffprobe_path, output, expected_seconds=1.0, tolerance=0.2)

    # Verify it is NOT the full 3 seconds
    data = probe_format(ffprobe_path, output)
    duration = float(data.get("format", {}).get("duration", 0))
    assert duration < 2.0, f"Clip should be ~1s, got {duration}s -- may not have trimmed"


@pytest.mark.integration
def test_extract_audio(test_video, tmp_path, ffprobe_path):
    """extract audio -- extract audio track as MP3."""
    output = tmp_path / "audio.mp3"
    result = runner.invoke(app, ["extract", "audio", str(test_video), str(output)])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]

    # Verify NO video stream in output
    assert len(video_streams) == 0, f"Expected no video streams, found {len(video_streams)}"

    # Verify audio stream exists
    assert len(audio_streams) > 0, "No audio stream in extracted audio"
    assert audio_streams[0]["codec_name"] == "mp3", f"Expected mp3, got {audio_streams[0]['codec_name']}"

    # Verify duration matches source (~3 seconds)
    assert_duration_approx(ffprobe_path, output, expected_seconds=3.0, tolerance=0.5)


@pytest.mark.integration
def test_extract_frames_single(test_video, tmp_path):
    """extract frames --at 0 -- extract a single frame as JPEG."""
    frame_path = tmp_path / "frame.jpg"
    result = runner.invoke(app, [
        "extract", "frames", str(test_video),
        "--at", "0",
        "--output-pattern", str(frame_path),
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(frame_path)

    # Verify output is a valid JPEG (starts with 0xFF 0xD8) or PNG (starts with 0x89 0x50)
    with open(frame_path, "rb") as f:
        header = f.read(2)
    is_jpeg = header == b"\xff\xd8"
    is_png = header == b"\x89\x50"
    assert is_jpeg or is_png, f"Not a valid JPEG or PNG. First 2 bytes: {header.hex()}"


# ===========================================================================
# transform group
# ===========================================================================


@pytest.mark.integration
def test_transform_resize(test_video, tmp_path, ffprobe_path):
    """transform resize -- resize to width=160, verify output width."""
    output = tmp_path / "resized.mp4"
    result = runner.invoke(app, [
        "transform", "resize", str(test_video), str(output),
        "--width", "160",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    assert len(video_streams) > 0, "No video stream in resized output"

    vs = video_streams[0]
    actual_width = int(vs["width"])
    actual_height = int(vs["height"])

    # Verify EXACT width = 160
    assert actual_width == 160, f"Expected width=160, got {actual_width}"

    # Verify height is even (required for H.264)
    assert actual_height % 2 == 0, f"Height {actual_height} is odd -- invalid for H.264"

    # For 320x240 scaled to 160 wide, height should be 120
    assert actual_height == 120, f"Expected height=120 (aspect ratio preserved), got {actual_height}"

    # Verify pixel format is yuv420p
    assert vs.get("pix_fmt") == "yuv420p", f"Expected yuv420p, got {vs.get('pix_fmt')}"


@pytest.mark.integration
def test_transform_rotate_90(test_video, tmp_path, ffprobe_path):
    """transform rotate --angle 90 -- verify width/height are swapped."""
    output = tmp_path / "rotated.mp4"
    result = runner.invoke(app, [
        "transform", "rotate", str(test_video), str(output),
        "--angle", "90",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    assert len(video_streams) > 0, "No video stream in rotated output"

    vs = video_streams[0]
    actual_width = int(vs["width"])
    actual_height = int(vs["height"])

    # Original is 320x240; after 90deg rotate should be 240x320
    assert actual_width == 240, f"Expected width=240 after rotation, got {actual_width}"
    assert actual_height == 320, f"Expected height=320 after rotation, got {actual_height}"


# ===========================================================================
# audio group
# ===========================================================================


@pytest.mark.integration
def test_audio_normalize(test_audio, tmp_path, ffprobe_path, ffmpeg_path):
    """audio normalize -- EBU R128 two-pass normalization hits target loudness."""
    output = tmp_path / "normalized.wav"
    result = runner.invoke(app, ["audio", "normalize", str(test_audio), str(output)])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    data = probe_format(ffprobe_path, output)
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]

    # Verify audio stream exists
    assert len(audio_streams) > 0, "No audio stream in normalized output"

    # Verify sample rate is 48000 (per the -ar 48000 flag in normalize command)
    assert audio_streams[0].get("sample_rate") == "48000", (
        f"Expected sample_rate=48000, got {audio_streams[0].get('sample_rate')}"
    )

    # Measure actual loudness of the output using loudnorm analysis pass
    measure_result = subprocess.run([
        ffmpeg_path, "-i", str(output),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-",
    ], capture_output=True, text=True)
    # Parse the loudnorm JSON from stderr
    stderr = measure_result.stderr
    import json as json_mod
    json_start = stderr.rfind("{")
    json_end = stderr.rfind("}") + 1
    if json_start >= 0 and json_end > json_start:
        loudness_data = json_mod.loads(stderr[json_start:json_end])
        measured_i = float(loudness_data.get("input_i", 0))
        # Output loudness should be within 1.5 LUFS of target (-16)
        assert abs(measured_i - (-16.0)) < 1.5, (
            f"Expected loudness ~-16 LUFS, got {measured_i} LUFS"
        )


# ===========================================================================
# combine group
# ===========================================================================


@pytest.mark.integration
def test_combine_concat(test_video, tmp_path, ffprobe_path):
    """combine concat -- concatenate test_video with itself, verify ~6s duration."""
    output = tmp_path / "concat.mp4"
    result = runner.invoke(app, [
        "combine", "concat", str(output),
        "--files", str(test_video),
        "--files", str(test_video),
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    # Verify duration is approximately DOUBLE the input (6s for two 3s clips)
    assert_duration_approx(ffprobe_path, output, expected_seconds=6.0, tolerance=0.5)


@pytest.mark.integration
def test_combine_from_images(test_image_sequence, tmp_path, ffprobe_path):
    """combine from-images -- create video from image sequence."""
    output = tmp_path / "from_images.mp4"
    result = runner.invoke(app, [
        "combine", "from-images", str(output),
        "--pattern", str(test_image_sequence),
        "--framerate", "10",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    assert len(video_streams) > 0, "No video stream found in output"

    # Verify H.264 codec
    assert video_streams[0]["codec_name"] == "h264", (
        f"Expected h264, got {video_streams[0]['codec_name']}"
    )

    # 10 frames at 10fps = ~1 second duration
    duration = float(data.get("format", {}).get("duration", 0))
    assert 0.5 <= duration <= 2.0, (
        f"Expected ~1s duration for 10 frames at 10fps, got {duration}s"
    )


# ===========================================================================
# util group
# ===========================================================================


@pytest.mark.integration
def test_util_probe(test_video):
    """util probe -- exit code 0, output contains video info as valid JSON."""
    result = runner.invoke(app, ["util", "probe", str(test_video), "--json"])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"

    # Parse the output as JSON and verify expected keys
    # The output may have non-JSON prefix lines, so find the JSON block
    output_text = result.output
    json_start = output_text.find("{")
    assert json_start >= 0, f"No JSON object found in probe output:\n{output_text[:500]}"
    json_text = output_text[json_start:]
    data = json.loads(json_text)

    # Verify expected structure
    assert "streams" in data, "Probe JSON missing 'streams' key"
    video_streams = [s for s in data["streams"] if s.get("codec_type") == "video"]
    assert len(video_streams) > 0, "No video stream in probe output"

    vs = video_streams[0]
    assert "codec_name" in vs, "Video stream missing 'codec_name'"
    assert "width" in vs, "Video stream missing 'width'"
    assert "height" in vs, "Video stream missing 'height'"
    assert int(vs["width"]) == 320, f"Expected width=320, got {vs['width']}"
    assert int(vs["height"]) == 240, f"Expected height=240, got {vs['height']}"


# ===========================================================================
# NEW TESTS: additional coverage
# ===========================================================================


@pytest.mark.integration
def test_convert_platform_youtube(test_video, tmp_path, ffprobe_path):
    """convert platform --platform youtube -- verify H.264 High profile, AAC, yuv420p."""
    output = tmp_path / "youtube.mp4"
    result = runner.invoke(app, [
        "convert", "platform", str(test_video), str(output),
        "--platform", "youtube",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]

    assert len(video_streams) > 0, "No video stream in YouTube output"
    vs = video_streams[0]

    # Verify H.264
    assert vs["codec_name"] == "h264", f"Expected h264, got {vs['codec_name']}"

    # Verify High profile (YouTube preset uses -preset slow which typically produces High)
    profile = vs.get("profile", "").lower()
    assert "high" in profile, f"Expected High profile for YouTube, got '{vs.get('profile')}'"

    # Verify yuv420p pixel format
    assert vs.get("pix_fmt") == "yuv420p", f"Expected yuv420p, got {vs.get('pix_fmt')}"

    # Verify AAC audio
    assert len(audio_streams) > 0, "No audio stream in YouTube output"
    assert audio_streams[0]["codec_name"] == "aac", f"Expected aac, got {audio_streams[0]['codec_name']}"


@pytest.mark.integration
def test_transform_crop_vertical(test_video, tmp_path, ffprobe_path):
    """transform crop --aspect 9:16 -- verify output is portrait (height > width)."""
    output = tmp_path / "vertical.mp4"
    result = runner.invoke(app, [
        "transform", "crop", str(test_video), str(output),
        "--aspect", "9:16",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    assert len(video_streams) > 0, "No video stream in cropped output"

    vs = video_streams[0]
    w = int(vs["width"])
    h = int(vs["height"])
    assert h > w, f"Expected portrait (height > width) but got {w}x{h}"

    # Verify actual 9:16 aspect ratio (tolerance for rounding)
    actual_ratio = w / h
    expected_ratio = 9 / 16  # 0.5625
    assert abs(actual_ratio - expected_ratio) < 0.05, \
        f"Expected 9:16 ratio (~0.5625) but got {actual_ratio:.4f} ({w}x{h})"


@pytest.mark.integration
def test_transform_fade(test_video, tmp_path, ffprobe_path, ffmpeg_path):
    """transform fade -- apply fade-in/out, verify fade was actually applied."""
    output = tmp_path / "faded.mp4"
    result = runner.invoke(app, [
        "transform", "fade", str(test_video), str(output),
        "--fade-in", "1", "--fade-out", "1",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    # Duration should match input (~3 seconds) -- fade doesn't change duration
    assert_duration_approx(ffprobe_path, output, expected_seconds=3.0, tolerance=0.5)

    # Verify fade was actually applied: extract first frame and check it's mostly black.
    # A 1-second fade-in from black means frame 0 should be very dark.
    # A mostly-black JPEG compresses to a very small file size.
    first_frame = tmp_path / "first_frame.jpg"
    subprocess.run(
        [ffmpeg_path, "-y", "-i", str(output), "-frames:v", "1", "-q:v", "2", str(first_frame)],
        capture_output=True,
        check=True,
    )
    frame_size = first_frame.stat().st_size
    assert frame_size < 5000, (
        f"First frame JPEG is {frame_size} bytes -- expected < 5000 bytes for a "
        f"mostly-black fade-in frame. Fade may not have been applied."
    )


@pytest.mark.integration
def test_transform_watermark(test_video, test_logo, tmp_path, ffprobe_path, ffmpeg_path):
    """transform watermark -- overlay logo on video, verify watermark was actually applied."""
    output_wm = tmp_path / "watermarked.mp4"
    output_plain = tmp_path / "plain.mp4"

    # Encode without watermark as a baseline
    subprocess.run(
        [ffmpeg_path, "-y", "-i", str(test_video), "-c:v", "libx264", "-crf", "23", str(output_plain)],
        capture_output=True,
        check=True,
    )

    # Encode with watermark
    result = runner.invoke(app, [
        "transform", "watermark", str(test_video), str(output_wm),
        "--logo", str(test_logo),
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output_wm)

    data = probe_format(ffprobe_path, output_wm)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    assert len(video_streams) > 0, "No video stream in watermarked output"

    # Verify watermark actually changed pixel content: the watermarked file must
    # have a different size from the plain re-encode at the same base settings.
    # A straight copy or identity filter would produce identical (or near-identical) output.
    wm_size = output_wm.stat().st_size
    plain_size = output_plain.stat().st_size
    assert wm_size != plain_size, (
        f"Watermarked file ({wm_size} bytes) is the same size as plain encode ({plain_size} bytes). "
        f"Watermark overlay may not have been applied."
    )


@pytest.mark.integration
def test_combine_mux(test_video, test_audio, tmp_path, ffprobe_path):
    """combine mux -- mux video-only + audio, verify both streams present."""
    # First extract video-only from test_video
    video_only = tmp_path / "video_only.mp4"
    import shutil
    ffmpeg_exe = shutil.which("ffmpeg")
    subprocess.run([
        ffmpeg_exe, "-y", "-i", str(test_video),
        "-an", "-c:v", "copy", str(video_only),
    ], check=True, capture_output=True)

    output = tmp_path / "muxed.mp4"
    result = runner.invoke(app, [
        "combine", "mux", str(output),
        "--video", str(video_only),
        "--audio", str(test_audio),
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]

    assert len(video_streams) > 0, "No video stream in muxed output"
    assert len(audio_streams) > 0, "No audio stream in muxed output"
