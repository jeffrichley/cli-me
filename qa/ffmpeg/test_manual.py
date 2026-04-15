"""Tier 3 manual tests for the ffmpeg skill CLI.

These tests generate real output files to a persistent directory and print
paths + instructions for human review.

Marker: manual
"""

from __future__ import annotations

import shutil
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

from conftest import assert_file_exists_and_nonzero  # noqa: E402

runner = CliRunner()

# Persistent output directory for manual review
MANUAL_DIR = Path(__file__).parent.parent / "fixtures" / "manual-review"


def _size_str(path: Path) -> str:
    """Human-readable file size."""
    size = path.stat().st_size
    if size > 1_000_000:
        return f"{size / 1_000_000:.1f} MB"
    elif size > 1_000:
        return f"{size / 1_000:.1f} KB"
    return f"{size} bytes"


# ===========================================================================
# Manual tests
# ===========================================================================


@pytest.mark.manual
def test_manual_gif_quality(test_video, ffprobe_path):
    """Generate a GIF and verify visual quality."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "gif_quality_test.gif"

    result = runner.invoke(app, [
        "convert", "to-gif", str(test_video), str(output),
        "--fps", "15", "--width", "320",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: GIF Quality")
    print(f"Output: {output}")
    print(f"Size: {_size_str(output)}")
    print(f"\nVerify:")
    print(f"  - Colors are smooth, no heavy banding")
    print(f"  - Animation is fluid at 15fps")
    print(f"  - Resolution looks correct (~320px wide)")
    print(f"  - No black frames at start/end")
    print(f"{'='*60}")


@pytest.mark.manual
def test_manual_compress_quality(test_video, ffprobe_path):
    """Compare CRF 18 vs CRF 28 side by side."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_crf18 = output_dir / "compress_crf18.mp4"
    output_crf28 = output_dir / "compress_crf28.mp4"

    result1 = runner.invoke(app, [
        "convert", "compress", str(test_video), str(output_crf18),
        "--crf", "18", "--preset", "medium",
    ])
    assert result1.exit_code == 0, f"CRF 18 failed (exit {result1.exit_code}):\n{result1.output}"

    result2 = runner.invoke(app, [
        "convert", "compress", str(test_video), str(output_crf28),
        "--crf", "28", "--preset", "medium",
    ])
    assert result2.exit_code == 0, f"CRF 28 failed (exit {result2.exit_code}):\n{result2.output}"

    assert_file_exists_and_nonzero(output_crf18)
    assert_file_exists_and_nonzero(output_crf28)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: Compression Quality Comparison")
    print(f"CRF 18 (high quality): {output_crf18}")
    print(f"  Size: {_size_str(output_crf18)}")
    print(f"CRF 28 (low quality):  {output_crf28}")
    print(f"  Size: {_size_str(output_crf28)}")
    print(f"\nVerify:")
    print(f"  - CRF 18 should be visually sharper than CRF 28")
    print(f"  - CRF 28 may show blocking artifacts on motion")
    print(f"  - CRF 18 file should be noticeably larger")
    print(f"  - Both should play without errors")
    print(f"{'='*60}")


@pytest.mark.manual
def test_manual_subtitle_burn(test_video, test_srt, ffprobe_path):
    """Verify subtitles are visible and positioned correctly."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "subtitle_burn_test.mp4"

    result = runner.invoke(app, [
        "transform", "subtitles", str(test_video), str(output),
        "--srt", str(test_srt),
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: Subtitle Burn-in")
    print(f"Output: {output}")
    print(f"Size: {_size_str(output)}")
    print(f"\nVerify:")
    print(f"  - 'Hello World' visible at 0:00-1:30")
    print(f"  - 'Test Subtitle' visible at 1:30-3:00")
    print(f"  - Text is centered at bottom of frame")
    print(f"  - Text is readable (good contrast)")
    print(f"  - No subtitle text bleeding off-screen")
    print(f"{'='*60}")


@pytest.mark.manual
def test_manual_watermark_placement(test_video, test_logo, ffprobe_path):
    """Verify logo is in the right corner with correct opacity."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "watermark_placement_test.mp4"

    result = runner.invoke(app, [
        "transform", "watermark", str(test_video), str(output),
        "--logo", str(test_logo),
        "--position", "br",
        "--opacity", "0.5",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: Watermark Placement")
    print(f"Output: {output}")
    print(f"Size: {_size_str(output)}")
    print(f"\nVerify:")
    print(f"  - Logo is visible in bottom-right corner")
    print(f"  - Logo is at ~50% opacity (semi-transparent)")
    print(f"  - Logo does not obscure important content")
    print(f"  - Logo stays fixed throughout the video")
    print(f"  - No visual artifacts around logo edges")
    print(f"{'='*60}")


@pytest.mark.manual
def test_manual_crop_vertical(test_video, ffprobe_path):
    """Verify 9:16 crop is centered correctly."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "crop_vertical_test.mp4"

    result = runner.invoke(app, [
        "transform", "crop", str(test_video), str(output),
        "--aspect", "9:16",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: 9:16 Vertical Crop")
    print(f"Output: {output}")
    print(f"Size: {_size_str(output)}")
    print(f"\nVerify:")
    print(f"  - Video is in portrait orientation (taller than wide)")
    print(f"  - Crop is centered horizontally on the source")
    print(f"  - No important content cut off at edges")
    print(f"  - Aspect ratio looks correct for phone/TikTok format")
    print(f"{'='*60}")


@pytest.mark.manual
def test_manual_audio_normalize(test_audio, ffprobe_path):
    """Listen to before/after normalization."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "audio_normalize_test.wav"

    # Also copy the original for comparison
    original_copy = output_dir / "audio_normalize_original.wav"
    shutil.copy2(test_audio, original_copy)

    result = runner.invoke(app, ["audio", "normalize", str(test_audio), str(output)])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: Audio Normalization")
    print(f"Original: {original_copy}")
    print(f"  Size: {_size_str(original_copy)}")
    print(f"Normalized: {output}")
    print(f"  Size: {_size_str(output)}")
    print(f"\nVerify:")
    print(f"  - Normalized audio is at consistent loudness level")
    print(f"  - No clipping or distortion in normalized output")
    print(f"  - Audio quality is preserved (no artifacts)")
    print(f"  - Volume difference is audible between original and normalized")
    print(f"{'='*60}")


@pytest.mark.manual
def test_manual_speed_change(test_video, ffprobe_path):
    """Verify 2x speed looks/sounds right."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "speed_2x_test.mp4"

    result = runner.invoke(app, [
        "transform", "speed", str(test_video), str(output),
        "--factor", "2.0",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: 2x Speed Change")
    print(f"Output: {output}")
    print(f"Size: {_size_str(output)}")
    print(f"\nVerify:")
    print(f"  - Video plays at 2x speed (~1.5s for 3s source)")
    print(f"  - Motion is smooth, no frame skipping artifacts")
    print(f"  - Audio pitch is correct (should sound sped up)")
    print(f"  - No audio/video sync issues")
    print(f"{'='*60}")


@pytest.mark.manual
def test_manual_fade_transitions(test_video, ffprobe_path):
    """Verify fade in/out looks smooth."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "fade_transitions_test.mp4"

    result = runner.invoke(app, [
        "transform", "fade", str(test_video), str(output),
        "--fade-in", "1.0", "--fade-out", "1.0",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: Fade Transitions")
    print(f"Output: {output}")
    print(f"Size: {_size_str(output)}")
    print(f"\nVerify:")
    print(f"  - Video fades in from black over first 1 second")
    print(f"  - Video fades out to black over last 1 second")
    print(f"  - Fade is smooth and gradual (no sudden jumps)")
    print(f"  - Audio also fades in/out with the video")
    print(f"  - Middle section plays at full brightness/volume")
    print(f"{'='*60}")


@pytest.mark.manual
def test_manual_resize_quality(test_video, ffprobe_path):
    """Verify no blurriness or artifacts after resize."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "resize_quality_test.mp4"

    result = runner.invoke(app, [
        "transform", "resize", str(test_video), str(output),
        "--width", "640",
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: Resize Quality (320 -> 640)")
    print(f"Output: {output}")
    print(f"Size: {_size_str(output)}")
    print(f"\nVerify:")
    print(f"  - Video is upscaled to ~640px wide")
    print(f"  - No excessive blurriness from upscaling")
    print(f"  - No ringing or halo artifacts around edges")
    print(f"  - Aspect ratio is preserved (no stretching)")
    print(f"  - Text/patterns in test source remain readable")
    print(f"{'='*60}")


@pytest.mark.manual
def test_manual_concat_seamless(test_video, ffprobe_path):
    """Verify no glitch at the join point."""
    output_dir = MANUAL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "concat_seamless_test.mp4"

    result = runner.invoke(app, [
        "combine", "concat", str(output),
        "--files", str(test_video),
        "--files", str(test_video),
    ])
    assert result.exit_code == 0, f"Command failed (exit {result.exit_code}):\n{result.output}"
    assert_file_exists_and_nonzero(output)

    print(f"\n{'='*60}")
    print(f"MANUAL REVIEW: Concatenation Seamlessness")
    print(f"Output: {output}")
    print(f"Size: {_size_str(output)}")
    print(f"\nVerify:")
    print(f"  - Video plays for ~6 seconds (two 3s clips)")
    print(f"  - No visual glitch/flash at the ~3 second join point")
    print(f"  - No audio pop or gap at the join point")
    print(f"  - Playback is continuous and smooth")
    print(f"  - Seek around the join point -- no decoder errors")
    print(f"{'='*60}")
