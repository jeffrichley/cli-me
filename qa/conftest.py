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
def ytdlp_path():
    """Return yt-dlp path or skip if not installed."""
    path = shutil.which("yt-dlp")
    if path is None:
        # Check common Windows pip install location
        import sys
        if sys.platform == "win32":
            from pathlib import Path as P
            for scripts_dir in P.home().glob("AppData/Roaming/Python/Python3*/Scripts"):
                candidate = scripts_dir / "yt-dlp.exe"
                if candidate.exists():
                    return str(candidate)
        pytest.skip("yt-dlp not found in PATH")
    return path


@pytest.fixture
def demucs_path():
    """Return demucs path or skip if not installed."""
    path = shutil.which("demucs")
    if path is None:
        # Check common Windows pip install locations
        import sys
        if sys.platform == "win32":
            from pathlib import Path as P
            for scripts_dir in P.home().glob("AppData/Roaming/Python/Python3*/Scripts"):
                candidate = scripts_dir / "demucs.exe"
                if candidate.exists():
                    return str(candidate)
            for scripts_dir in P.home().glob("AppData/Local/Programs/Python/Python3*/Scripts"):
                candidate = scripts_dir / "demucs.exe"
                if candidate.exists():
                    return str(candidate)
        pytest.skip("demucs not found in PATH")
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
# Moved to qa/_helpers.py — see that module's docstring for why.
# Tests should import directly from _helpers (after adding qa/ to sys.path).
