"""Tier 2: Integration tests for download commands against real yt-dlp.

These tests download real content and verify output properties.
Skips if yt-dlp is not installed.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Add the scripts directory to the path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "skill-repo" / "yt-dlp" / "scripts")
)

from yt_dlp_cli.commands import download_video, download_audio

# Short Creative Commons video for testing
# "Big Buck Bunny" trailer — 33 seconds, public domain
TEST_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"


@pytest.mark.integration
class TestDownloadVideoIntegration:
    """Integration tests for download video command."""

    def test_download_default(self, ytdlp_path, ffprobe_path, tmp_path):
        """Download with default settings produces a video+audio file."""
        args = download_video.build_args(
            TEST_URL,
            output=str(tmp_path / "%(id)s.%(ext)s"),
            max_height=360,  # Keep small for test speed
        )
        result = subprocess.run(
            [ytdlp_path] + args,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"yt-dlp failed: {result.stderr}"

        # Find the downloaded file
        files = list(tmp_path.glob("aqz-KE-bpKQ.*"))
        assert len(files) >= 1, f"No output file found in {tmp_path}"
        output_file = files[0]

        # Deep assertions: verify video and audio streams exist
        probe_result = subprocess.run(
            [ffprobe_path, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(output_file)],
            capture_output=True, text=True,
        )
        probe_data = json.loads(probe_result.stdout)
        stream_types = [s["codec_type"] for s in probe_data.get("streams", [])]
        assert "video" in stream_types, "Downloaded file has no video stream"
        assert "audio" in stream_types, "Downloaded file has no audio stream"

        # Verify max_height was respected
        video_stream = next(s for s in probe_data["streams"] if s["codec_type"] == "video")
        height = int(video_stream["height"])
        assert height <= 360, f"Expected height <= 360, got {height}"

        # Verify file is non-trivial size (> 100KB for a 33s video)
        assert output_file.stat().st_size > 100_000, "File too small — likely corrupt"


@pytest.mark.integration
class TestDownloadAudioIntegration:
    """Integration tests for download audio command."""

    def test_download_audio_mp3(self, ytdlp_path, ffprobe_path, tmp_path):
        """Download audio as MP3 produces an audio-only file."""
        args = download_audio.build_args(
            TEST_URL,
            format="mp3",
            quality="medium",
            output=str(tmp_path / "%(id)s.%(ext)s"),
        )
        result = subprocess.run(
            [ytdlp_path] + args,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"yt-dlp failed: {result.stderr}"

        # Find the MP3 file
        files = list(tmp_path.glob("aqz-KE-bpKQ.mp3"))
        assert len(files) == 1, f"Expected 1 MP3 file, found: {list(tmp_path.iterdir())}"
        output_file = files[0]

        # Deep assertions
        probe_result = subprocess.run(
            [ffprobe_path, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(output_file)],
            capture_output=True, text=True,
        )
        probe_data = json.loads(probe_result.stdout)
        stream_types = [s["codec_type"] for s in probe_data.get("streams", [])]
        assert "audio" in stream_types, "MP3 file has no audio stream"

        # Verify it's actually MP3 codec
        audio_stream = next(s for s in probe_data["streams"] if s["codec_type"] == "audio")
        assert audio_stream["codec_name"] == "mp3", f"Expected mp3 codec, got {audio_stream['codec_name']}"

        # Verify duration is positive and reasonable (video length varies)
        duration = float(probe_data["format"]["duration"])
        assert duration > 10, f"Duration {duration}s too short — likely corrupt"

        # Verify file size (MP3 should be substantial)
        assert output_file.stat().st_size > 50_000, "MP3 file too small"
