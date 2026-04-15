"""QA test framework for cli-me skills.

Three tiers:
- Tier 1 (command_graph): Tests CLI builds correct args. No binary needed. Always runs.
- Tier 2 (integration): Tests against real binary. Skips if binary missing.
- Tier 3 (manual): Opens output for human review. Never in CI.
"""

import os
import shutil
import subprocess
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line("markers", "command_graph: Tier 1 — tests command construction (no binary)")
    config.addinivalue_line("markers", "integration: Tier 2 — tests against real binary (skips if missing)")
    config.addinivalue_line("markers", "manual: Tier 3 — requires human review (skip in CI)")


# ---------------------------------------------------------------------------
# Binary detection fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ffmpeg_path():
    """Return ffmpeg path or skip if not installed."""
    path = shutil.which("ffmpeg")
    if path is None:
        pytest.skip("ffmpeg not found in PATH")
    return path


@pytest.fixture
def ffprobe_path():
    """Return ffprobe path or skip if not installed."""
    path = shutil.which("ffprobe")
    if path is None:
        pytest.skip("ffprobe not found in PATH")
    return path


# ---------------------------------------------------------------------------
# Synthetic fixture generators
# ---------------------------------------------------------------------------

@pytest.fixture
def test_video(tmp_path, ffmpeg_path):
    """Generate a 3-second 320x240 test video with audio."""
    output = tmp_path / "test_input.mp4"
    subprocess.run([
        ffmpeg_path, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "64k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output),
    ], check=True, capture_output=True)
    return output


@pytest.fixture
def test_audio(tmp_path, ffmpeg_path):
    """Generate a 3-second test audio file (WAV)."""
    output = tmp_path / "test_input.wav"
    subprocess.run([
        ffmpeg_path, "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        str(output),
    ], check=True, capture_output=True)
    return output


@pytest.fixture
def test_image(tmp_path, ffmpeg_path):
    """Generate a single test image (PNG)."""
    output = tmp_path / "test_input.png"
    subprocess.run([
        ffmpeg_path, "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1",
        "-frames:v", "1",
        str(output),
    ], check=True, capture_output=True)
    return output


@pytest.fixture
def test_image_sequence(tmp_path, ffmpeg_path):
    """Generate a sequence of 10 numbered test images."""
    pattern = tmp_path / "frame_%04d.png"
    subprocess.run([
        ffmpeg_path, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=10",
        str(pattern),
    ], check=True, capture_output=True)
    return str(pattern)


@pytest.fixture
def test_srt(tmp_path):
    """Generate a simple SRT subtitle file."""
    srt = tmp_path / "test.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:01,500\nHello World\n\n"
        "2\n00:00:01,500 --> 00:00:03,000\nTest Subtitle\n"
    )
    return srt


@pytest.fixture
def test_logo(tmp_path, ffmpeg_path):
    """Generate a small PNG logo with transparency."""
    output = tmp_path / "logo.png"
    subprocess.run([
        ffmpeg_path, "-y",
        "-f", "lavfi", "-i", "color=c=red@0.5:s=80x80:d=1",
        "-frames:v", "1",
        str(output),
    ], check=True, capture_output=True)
    return output


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def assert_file_exists_and_nonzero(path):
    """Assert a file exists and has size > 0."""
    p = Path(path)
    assert p.exists(), f"Output file does not exist: {path}"
    assert p.stat().st_size > 0, f"Output file is empty: {path}"


def probe_format(ffprobe_path, file_path) -> dict:
    """Run ffprobe and return parsed JSON."""
    result = subprocess.run([
        ffprobe_path, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(file_path),
    ], capture_output=True, text=True)
    import json
    return json.loads(result.stdout)


def assert_video_properties(ffprobe_path, file_path, *, codec=None, width=None, height=None):
    """Assert video stream properties."""
    data = probe_format(ffprobe_path, file_path)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    assert len(video_streams) > 0, f"No video stream in {file_path}"
    vs = video_streams[0]
    if codec:
        assert vs["codec_name"] == codec, f"Expected codec {codec}, got {vs['codec_name']}"
    if width:
        assert int(vs["width"]) == width, f"Expected width {width}, got {vs['width']}"
    if height:
        assert int(vs["height"]) == height, f"Expected height {height}, got {vs['height']}"


def assert_audio_properties(ffprobe_path, file_path, *, codec=None, sample_rate=None):
    """Assert audio stream properties."""
    data = probe_format(ffprobe_path, file_path)
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    assert len(audio_streams) > 0, f"No audio stream in {file_path}"
    aus = audio_streams[0]
    if codec:
        assert aus["codec_name"] == codec, f"Expected codec {codec}, got {aus['codec_name']}"
    if sample_rate:
        assert aus["sample_rate"] == str(sample_rate), f"Expected sample rate {sample_rate}, got {aus['sample_rate']}"


def assert_duration_approx(ffprobe_path, file_path, expected_seconds, tolerance=0.5):
    """Assert file duration is approximately expected."""
    data = probe_format(ffprobe_path, file_path)
    duration = float(data.get("format", {}).get("duration", 0))
    assert abs(duration - expected_seconds) <= tolerance, \
        f"Expected duration ~{expected_seconds}s, got {duration}s"
