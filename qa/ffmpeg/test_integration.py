"""Tier 2 integration tests for the ffmpeg skill CLI.

These tests run real ffmpeg commands and verify output files.
Requires ffmpeg 7.x installed in PATH.

Marker: integration
"""

from __future__ import annotations

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
    assert_video_properties(ffprobe_path, output, codec="h264")


@pytest.mark.integration
def test_convert_format_copy(test_video, tmp_path, ffprobe_path):
    """convert format --copy -- transmux without re-encoding."""
    output = tmp_path / "output.mkv"
    result = runner.invoke(app, ["convert", "format", str(test_video), str(output), "--copy"])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)
    # Should keep the original codec (h264 from test_video fixture)
    assert_video_properties(ffprobe_path, output, codec="h264")


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
    assert output.stat().st_size < test_video.stat().st_size, (
        f"Compressed ({output.stat().st_size}) should be smaller than source ({test_video.stat().st_size})"
    )


@pytest.mark.integration
def test_convert_audio(test_audio, tmp_path, ffprobe_path):
    """convert audio -- WAV to MP3."""
    output = tmp_path / "output.mp3"
    result = runner.invoke(app, ["convert", "audio", str(test_audio), str(output)])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)
    assert_audio_properties(ffprobe_path, output, codec="mp3")


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
    assert_duration_approx(ffprobe_path, output, expected_seconds=1.0, tolerance=0.5)


@pytest.mark.integration
def test_extract_audio(test_video, tmp_path, ffprobe_path):
    """extract audio -- extract audio track as MP3."""
    output = tmp_path / "audio.mp3"
    result = runner.invoke(app, ["extract", "audio", str(test_video), str(output)])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)
    assert_audio_properties(ffprobe_path, output, codec="mp3")


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
    assert_video_properties(ffprobe_path, output, width=160)


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
    # Original is 320x240; after 90deg rotate should be 240x320
    assert_video_properties(ffprobe_path, output, width=240, height=320)


# ===========================================================================
# audio group
# ===========================================================================


@pytest.mark.integration
def test_audio_normalize(test_audio, tmp_path):
    """audio normalize -- EBU R128 two-pass normalization produces output."""
    output = tmp_path / "normalized.wav"
    result = runner.invoke(app, ["audio", "normalize", str(test_audio), str(output)])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)


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
    assert_duration_approx(ffprobe_path, output, expected_seconds=6.0, tolerance=1.0)


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
    # 10 frames at 10fps = ~1 second
    data = probe_format(ffprobe_path, output)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    assert len(video_streams) > 0, "No video stream found in output"


# ===========================================================================
# util group
# ===========================================================================


@pytest.mark.integration
def test_util_probe(test_video):
    """util probe -- exit code 0, output contains video info."""
    result = runner.invoke(app, ["util", "probe", str(test_video), "--json"])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    # JSON output should contain stream info
    assert '"codec_type"' in result.output or "codec_type" in result.output, (
        f"Expected codec_type in probe output, got:\n{result.output[:500]}"
    )
