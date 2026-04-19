"""Shared assertion helpers for QA integration tests.

These are plain functions (not pytest fixtures) used by integration test
modules across skills. They live in their own module — not in conftest.py —
because conftest is meant to be auto-loaded by pytest, not imported by name.

Tests import via: ``from _helpers import assert_audio_properties, ...``
after adding ``qa/`` to sys.path (each test that needs these helpers does
that itself).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


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
