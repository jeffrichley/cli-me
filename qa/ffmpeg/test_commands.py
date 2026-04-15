"""Tier 1 command-graph tests for the ffmpeg skill CLI.

These tests verify that each command constructs the correct ffmpeg/ffprobe
argument lists WITHOUT invoking any real binary. subprocess.run is mocked
throughout.

Marker: command_graph
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup — skill lives outside the qa/ tree
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skill-repo" / "ffmpeg" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from typer.testing import CliRunner

from ffmpeg_cli import app  # noqa: E402  (after sys.path manipulation)

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_FFMPEG = "/usr/bin/ffmpeg"
FAKE_FFPROBE = "/usr/bin/ffprobe"


def _make_run(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Return a mock CompletedProcess."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _which_side_effect(name: str) -> str:
    """Return a fake path for ffmpeg or ffprobe."""
    return FAKE_FFMPEG if name == "ffmpeg" else FAKE_FFPROBE


# ---------------------------------------------------------------------------
# Group: convert
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestConvertFormat:
    """convert format — stream copy and re-encode modes."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_copy_mode(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["convert", "format", "input.mp4", "output.mp4", "--copy"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert args[0] == FAKE_FFMPEG
        assert "-c" in args
        copy_idx = args.index("-c")
        assert args[copy_idx + 1] == "copy"
        assert "-movflags" in args
        assert "+faststart" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_reencode_default_crf(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["convert", "format", "input.mp4", "output.mp4"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-c:v" in args
        assert "libx264" in args
        assert "-crf" in args
        crf_idx = args.index("-crf")
        assert args[crf_idx + 1] == "23"
        assert "-pix_fmt" in args and "yuv420p" in args
        assert "-c:a" in args and "aac" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_custom_crf(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["convert", "format", "in.mp4", "out.mp4", "--crf", "18"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        crf_idx = args.index("-crf")
        assert args[crf_idx + 1] == "18"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_custom_codec(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["convert", "format", "in.mp4", "out.mp4", "--codec", "libx265"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "libx265" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_faststart_always_present(self, mock_which, mock_run):
        """Both copy and re-encode modes should include -movflags +faststart."""
        mock_run.return_value = _make_run()
        for extra in [[], ["--copy"]]:
            result = runner.invoke(app, ["convert", "format", "i.mp4", "o.mp4"] + extra)
            assert result.exit_code == 0, result.output
            args = mock_run.call_args[0][0]
            assert "+faststart" in args


@pytest.mark.command_graph
class TestConvertCompress:
    """convert compress — CRF mode and two-pass target-size mode."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_crf_mode(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["convert", "compress", "in.mp4", "out.mp4", "--crf", "28"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-crf" in args
        crf_idx = args.index("-crf")
        assert args[crf_idx + 1] == "28"
        assert "-c:v" in args and "libx264" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_two_pass_mode_calls_ffmpeg_twice(self, mock_which, mock_run):
        """Two-pass: first call has -pass 1, second has -pass 2."""
        # Simulate ffprobe duration response for get_duration
        probe_response = _make_run(
            stdout='{"format":{"duration":"10.0"},"streams":[]}'
        )
        # Both ffmpeg pass calls succeed
        ffmpeg_response = _make_run()
        mock_run.side_effect = [probe_response, ffmpeg_response, ffmpeg_response]

        result = runner.invoke(
            app, ["convert", "compress", "in.mp4", "out.mp4", "--target-size", "5"]
        )
        assert result.exit_code == 0, result.output
        assert mock_run.call_count == 3  # 1 ffprobe + 2 ffmpeg passes

        # Second call (pass 1) — index 1 in side_effect
        pass1_args = mock_run.call_args_list[1][0][0]
        assert "-pass" in pass1_args
        assert "1" in pass1_args
        assert "-an" in pass1_args
        assert "-f" in pass1_args and "null" in pass1_args

        # Third call (pass 2) — index 2
        pass2_args = mock_run.call_args_list[2][0][0]
        assert "-pass" in pass2_args
        assert "2" in pass2_args
        assert "-c:a" in pass2_args and "aac" in pass2_args


@pytest.mark.command_graph
class TestConvertPlatform:
    """convert platform — youtube, twitter, tiktok."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_youtube(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["convert", "platform", "in.mp4", "out.mp4", "--platform", "youtube"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        # Check flags by index
        crf_idx = args.index("-crf")
        assert args[crf_idx + 1] == "18"
        bf_idx = args.index("-bf")
        assert args[bf_idx + 1] == "2"
        ba_idx = args.index("-b:a")
        assert args[ba_idx + 1] == "384k"
        ar_idx = args.index("-ar")
        assert args[ar_idx + 1] == "48000"
        assert "-profile:v" in args
        assert args[args.index("-profile:v") + 1] == "high"
        assert "-ac" in args
        assert args[args.index("-ac") + 1] == "2"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_twitter(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["convert", "platform", "in.mp4", "out.mp4", "--platform", "twitter"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        # Verify profile and level by index
        assert "-profile:v" in args
        assert args[args.index("-profile:v") + 1] == "high"
        assert "-level:v" in args
        assert args[args.index("-level:v") + 1] == "4.0"
        # Verify scale filter contains min() expressions
        assert "-vf" in args
        vf_idx = args.index("-vf")
        vf_value = args[vf_idx + 1]
        assert "min(1280,iw)" in vf_value
        assert "min(720,ih)" in vf_value
        assert "pad=" in vf_value
        # Verify audio
        assert "-ac" in args
        assert args[args.index("-ac") + 1] == "2"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_tiktok(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["convert", "platform", "in.mp4", "out.mp4", "--platform", "tiktok"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        # Verify profile and level by index
        assert "-profile:v" in args
        assert args[args.index("-profile:v") + 1] == "high"
        assert "-level:v" in args
        assert args[args.index("-level:v") + 1] == "4.2"
        # Verify CRF and preset match wiki
        crf_idx = args.index("-crf")
        assert args[crf_idx + 1] == "18"
        preset_idx = args.index("-preset")
        assert args[preset_idx + 1] == "slow"
        # Verify scale filter has 1080x1920
        assert "-vf" in args
        vf_value = args[args.index("-vf") + 1]
        assert "1080" in vf_value and "1920" in vf_value
        # Verify audio bitrate and channels
        ba_idx = args.index("-b:a")
        assert args[ba_idx + 1] == "256k"
        assert "-ac" in args
        assert args[args.index("-ac") + 1] == "2"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_unknown_platform_exits(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["convert", "platform", "in.mp4", "out.mp4", "--platform", "myspace"]
        )
        assert result.exit_code != 0


@pytest.mark.command_graph
class TestConvertToGif:
    """convert to-gif — two-pass palette approach."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_two_pass_palette(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["convert", "to-gif", "in.mp4", "out.gif"])
        assert result.exit_code == 0, result.output
        assert mock_run.call_count == 2, "Expected exactly two ffmpeg calls (palette + encode)"

        # Pass 1: palette generation
        pass1_args = mock_run.call_args_list[0][0][0]
        pass1_str = " ".join(pass1_args)
        assert "palettegen" in pass1_str

        # Pass 2: encode with palette
        pass2_args = mock_run.call_args_list[1][0][0]
        pass2_str = " ".join(pass2_args)
        assert "paletteuse" in pass2_str
        assert "-lavfi" in pass2_args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_time_args_in_both_passes(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            ["convert", "to-gif", "in.mp4", "out.gif", "--start", "00:00:01", "--duration", "2"],
        )
        assert result.exit_code == 0, result.output
        for call_args in mock_run.call_args_list:
            args = call_args[0][0]
            assert "-ss" in args
            assert "-t" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_fps_and_width_in_filter(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["convert", "to-gif", "in.mp4", "out.gif", "--fps", "10", "--width", "320"]
        )
        assert result.exit_code == 0, result.output
        # Both passes should have fps=10,scale=320:-1
        for c in mock_run.call_args_list:
            args_str = " ".join(c[0][0])
            assert "fps=10" in args_str
            assert "scale=320" in args_str


# ---------------------------------------------------------------------------
# Group: extract
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestExtractClip:
    """extract clip — -ss placement, copy vs re-encode."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_ss_before_input(self, mock_which, mock_run):
        """Input-seeking: -ss must appear BEFORE -i."""
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            ["extract", "clip", "in.mp4", "out.mp4", "--start", "00:00:05", "--duration", "3"],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-ss" in args
        assert "-i" in args
        ss_idx = args.index("-ss")
        i_idx = args.index("-i")
        assert ss_idx < i_idx, "-ss must be placed before -i"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_copy_mode_flags(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "extract", "clip", "in.mp4", "out.mp4",
                "--start", "5", "--duration", "3", "--copy",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-c" in args
        c_idx = args.index("-c")
        assert args[c_idx + 1] == "copy"
        assert "-avoid_negative_ts" in args
        avoidts_idx = args.index("-avoid_negative_ts")
        assert args[avoidts_idx + 1] == "make_zero"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_reencode_mode_no_avoid_negative_ts(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            ["extract", "clip", "in.mp4", "out.mp4", "--start", "5", "--duration", "3"],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-c:v" in args and "libx264" in args
        assert "-avoid_negative_ts" not in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_end_timestamp(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            ["extract", "clip", "in.mp4", "out.mp4", "--start", "0", "--end", "00:00:05"],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-to" in args
        to_idx = args.index("-to")
        assert args[to_idx + 1] == "00:00:05"


@pytest.mark.command_graph
class TestExtractAudio:
    """-vn flag and codec selection by extension."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_vn_flag_present(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["extract", "audio", "in.mp4", "out.mp3"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-vn" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_mp3_codec(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["extract", "audio", "in.mp4", "out.mp3"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "libmp3lame" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_wav_codec(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["extract", "audio", "in.mp4", "out.wav"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "pcm_s16le" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_track_map(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["extract", "audio", "in.mkv", "out.aac", "--track", "1"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-map" in args
        map_idx = args.index("-map")
        assert args[map_idx + 1] == "0:a:1"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_cbr_bitrate_overrides_quality(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["extract", "audio", "in.mp4", "out.mp3", "--bitrate", "320k"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-b:a" in args
        ba_idx = args.index("-b:a")
        assert args[ba_idx + 1] == "320k"
        assert "-q:a" not in args


# ---------------------------------------------------------------------------
# Group: transform
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestTransformResize:
    """scale filter with -2 for even dimensions."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_width_only(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "resize", "in.mp4", "out.mp4", "--width", "1280"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-vf" in args
        vf_idx = args.index("-vf")
        assert "scale=1280:-2" in args[vf_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_height_only(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "resize", "in.mp4", "out.mp4", "--height", "720"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        assert "scale=-2:720" in args[vf_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_letterbox(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "transform", "resize", "in.mp4", "out.mp4",
                "--width", "1920", "--height", "1080", "--letterbox",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert "force_original_aspect_ratio=decrease" in vf
        assert "pad=" in vf

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_no_dimensions_exits(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["transform", "resize", "in.mp4", "out.mp4"])
        assert result.exit_code != 0


@pytest.mark.command_graph
class TestTransformCrop:
    """Crop expression uses ih as the height anchor."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_9_16_crop_default(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["transform", "crop", "in.mp4", "out.mp4"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert "crop=ih*9/16:ih" in vf

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_16_9_aspect(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "crop", "in.mp4", "out.mp4", "--aspect", "16:9"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert "crop=ih*16/9:ih" in vf

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_pad_mode(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "crop", "in.mp4", "out.mp4", "--pad"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert "pad=" in vf
        assert "crop=" not in vf


@pytest.mark.command_graph
class TestTransformRotate:
    """transpose mapping and flip filters."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_90_degrees(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "rotate", "in.mp4", "out.mp4", "--angle", "90"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        assert "transpose=1" in args[vf_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_180_degrees_is_two_transposes(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "rotate", "in.mp4", "out.mp4", "--angle", "180"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert vf.count("transpose=1") == 2

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_270_degrees(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "rotate", "in.mp4", "out.mp4", "--angle", "270"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        assert "transpose=2" in args[vf_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_hflip(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "rotate", "in.mp4", "out.mp4", "--flip", "h"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        assert "hflip" in args[vf_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_vflip(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "rotate", "in.mp4", "out.mp4", "--flip", "v"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        assert "vflip" in args[vf_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_invalid_angle_exits(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "rotate", "in.mp4", "out.mp4", "--angle", "45"]
        )
        assert result.exit_code != 0

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_no_flags_exits(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["transform", "rotate", "in.mp4", "out.mp4"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Group: audio
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestAudioNormalize:
    """EBU R128 two-pass loudness normalization."""

    _GOOD_LOUDNORM_JSON = """{
        "input_i": "-23.0",
        "input_tp": "-5.0",
        "input_lra": "7.0",
        "input_thresh": "-33.0",
        "output_i": "-16.0",
        "output_tp": "-1.5",
        "output_lra": "7.0",
        "output_thresh": "-26.0",
        "normalization_type": "dynamic",
        "target_offset": "0.0"
    }"""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_two_pass_approach(self, mock_which, mock_run):
        """Pass 1 measures; pass 2 applies with measured values."""
        pass1_result = _make_run(stderr=self._GOOD_LOUDNORM_JSON)
        pass2_result = _make_run()
        mock_run.side_effect = [pass1_result, pass2_result]

        result = runner.invoke(app, ["audio", "normalize", "in.wav", "out.wav"])
        assert result.exit_code == 0, result.output
        assert mock_run.call_count == 2

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_pass1_uses_loudnorm_and_null_output(self, mock_which, mock_run):
        pass1_result = _make_run(stderr=self._GOOD_LOUDNORM_JSON)
        pass2_result = _make_run()
        mock_run.side_effect = [pass1_result, pass2_result]

        runner.invoke(app, ["audio", "normalize", "in.wav", "out.wav"])
        pass1_args = mock_run.call_args_list[0][0][0]
        pass1_str = " ".join(pass1_args)
        assert "loudnorm=I=-16" in pass1_str
        assert "-f" in pass1_args
        f_idx = pass1_args.index("-f")
        assert pass1_args[f_idx + 1] == "null"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_pass2_includes_measured_values_and_48k(self, mock_which, mock_run):
        pass1_result = _make_run(stderr=self._GOOD_LOUDNORM_JSON)
        pass2_result = _make_run()
        mock_run.side_effect = [pass1_result, pass2_result]

        runner.invoke(app, ["audio", "normalize", "in.wav", "out.wav"])
        pass2_args = mock_run.call_args_list[1][0][0]
        pass2_str = " ".join(pass2_args)
        assert "measured_I=" in pass2_str
        assert "-ar" in pass2_args
        ar_idx = pass2_args.index("-ar")
        assert pass2_args[ar_idx + 1] == "48000"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_custom_target_lufs(self, mock_which, mock_run):
        pass1_result = _make_run(stderr=self._GOOD_LOUDNORM_JSON)
        pass2_result = _make_run()
        mock_run.side_effect = [pass1_result, pass2_result]

        runner.invoke(app, ["audio", "normalize", "in.wav", "out.wav", "--target", "-23"])
        pass1_args = mock_run.call_args_list[0][0][0]
        assert "loudnorm=I=-23" in " ".join(pass1_args)


# ---------------------------------------------------------------------------
# Group: combine
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestCombineConcat:
    """Demuxer mode writes filelist; filter mode uses -filter_complex."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_demuxer_mode_uses_concat_demuxer(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "combine", "concat", "out.mp4",
                "--files", "a.mp4", "--files", "b.mp4",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-f" in args
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "concat"
        assert "-safe" in args
        assert "-c" in args
        c_idx = args.index("-c")
        assert args[c_idx + 1] == "copy"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_filter_mode_uses_concat_filter(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "combine", "concat", "out.mp4",
                "--files", "a.mp4", "--files", "b.mp4", "--filter",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-filter_complex" in args
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "concat=n=2" in fc
        assert "v=1:a=1" in fc

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_filter_mode_three_files(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "combine", "concat", "out.mp4",
                "--files", "a.mp4", "--files", "b.mp4", "--files", "c.mp4",
                "--filter",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "concat=n=3" in fc


# ---------------------------------------------------------------------------
# Group: util
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestUtilProbe:
    """ffprobe args — quiet, json format, show_format, show_streams."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_ffprobe_args(self, mock_which, mock_run):
        mock_run.return_value = _make_run(
            stdout='{"format":{"duration":"5.0","size":"1000000","bit_rate":"1600000","format_name":"mp4","format_long_name":"QuickTime"},"streams":[]}'
        )
        result = runner.invoke(app, ["util", "probe", "in.mp4"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert args[0] == FAKE_FFPROBE
        assert "-v" in args
        v_idx = args.index("-v")
        assert args[v_idx + 1] == "quiet"
        assert "-print_format" in args
        pf_idx = args.index("-print_format")
        assert args[pf_idx + 1] == "json"
        assert "-show_format" in args
        assert "-show_streams" in args
        assert "in.mp4" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_json_flag_outputs_raw_json(self, mock_which, mock_run):
        import json
        payload = {
            "format": {
                "duration": "5.0",
                "size": "1000000",
                "bit_rate": "1600000",
                "format_name": "mp4",
            },
            "streams": [],
        }
        mock_run.return_value = _make_run(stdout=json.dumps(payload))
        result = runner.invoke(app, ["util", "probe", "in.mp4", "--json"])
        assert result.exit_code == 0, result.output
        # Output should be valid JSON
        parsed = json.loads(result.output)
        assert "format" in parsed


# ---------------------------------------------------------------------------
# Additional command-graph tests for completeness
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestExtractFrames:
    """Frame extraction modes."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_single_frame_at_timestamp(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["extract", "frames", "in.mp4", "--at", "00:00:01"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-ss" in args
        ss_idx = args.index("-ss")
        assert args[ss_idx + 1] == "00:00:01"
        # -ss before -i
        i_idx = args.index("-i")
        assert ss_idx < i_idx
        assert "-frames:v" in args
        fv_idx = args.index("-frames:v")
        assert args[fv_idx + 1] == "1"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_every_n_seconds(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["extract", "frames", "in.mp4", "--every", "2.0"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-vf" in args
        vf_idx = args.index("-vf")
        assert "fps=1/2.0" in args[vf_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_iframes_only(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["extract", "frames", "in.mp4", "--iframes"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-vf" in args
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert "select=" in vf
        assert "pict_type" in vf
        assert "-vsync" in args
        vsync_idx = args.index("-vsync")
        assert args[vsync_idx + 1] == "vfr"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_width_scaling_uses_minus_2(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["extract", "frames", "in.mp4", "--every", "1.0", "--width", "160"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert "scale=160:-2" in vf


@pytest.mark.command_graph
class TestAudioSilence:
    """silenceremove filter construction."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_default_filter(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["audio", "silence", "in.wav", "out.wav"])
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_idx = args.index("-af")
        af = args[af_idx + 1]
        assert "silenceremove" in af
        assert "stop_periods=-1" in af

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_custom_threshold(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["audio", "silence", "in.wav", "out.wav", "--threshold", "-40dB"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        af_idx = args.index("-af")
        assert "stop_threshold=-40dB" in args[af_idx + 1]


@pytest.mark.command_graph
class TestCombineMux:
    """Video/audio mux with optional delay."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_basic_mux(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            ["combine", "mux", "out.mp4", "--video", "v.mp4", "--audio", "a.wav"],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-map" in args
        # Two -map flags: video and audio
        map_indices = [i for i, a in enumerate(args) if a == "-map"]
        assert len(map_indices) >= 2
        assert "0:v:0" in args
        assert "1:a:0" in args
        assert "-c" in args
        c_idx = args.index("-c")
        assert args[c_idx + 1] == "copy"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_delay_itsoffset_before_audio_input(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "combine", "mux", "out.mp4",
                "--video", "v.mp4", "--audio", "a.wav", "--delay", "0.5",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-itsoffset" in args
        itsoffset_idx = args.index("-itsoffset")
        # itsoffset must come before the audio -i
        audio_i_idx = None
        for i, a in enumerate(args):
            if a == "-i" and i > itsoffset_idx:
                audio_i_idx = i
                break
        assert audio_i_idx is not None, "-i for audio must follow -itsoffset"


@pytest.mark.command_graph
class TestCombineFromImages:
    """-framerate before -i, yuv420p pixel format."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_framerate_before_input(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            ["combine", "from-images", "out.mp4", "--pattern", "frame_%04d.png"],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-framerate" in args
        fr_idx = args.index("-framerate")
        assert args[fr_idx + 1] == "24"
        i_idx = args.index("-i")
        assert fr_idx < i_idx
        assert "yuv420p" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_custom_framerate(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "combine", "from-images", "out.mp4",
                "--pattern", "frame_%04d.png", "--framerate", "30",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        fr_idx = args.index("-framerate")
        assert args[fr_idx + 1] == "30"


# ---------------------------------------------------------------------------
# NEW Tier 1 tests — 17 previously untested commands
# ---------------------------------------------------------------------------


@pytest.mark.command_graph
class TestConvertHwaccel:
    """convert hwaccel — encoder selection, quality flag, HEVC variant."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_nvenc_h264_encoder_and_quality_flag(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["convert", "hwaccel", "in.mp4", "out.mp4", "--encoder", "nvenc"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-c:v" in args
        cv_idx = args.index("-c:v")
        assert args[cv_idx + 1] == "h264_nvenc"
        assert "-cq" in args
        cq_idx = args.index("-cq")
        assert args[cq_idx + 1] == "23"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_nvenc_hevc_variant(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["convert", "hwaccel", "in.mp4", "out.mp4", "--encoder", "nvenc", "--hevc"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        cv_idx = args.index("-c:v")
        assert args[cv_idx + 1] == "hevc_nvenc"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_vaapi_encoder_and_device_flag(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["convert", "hwaccel", "in.mp4", "out.mp4", "--encoder", "vaapi"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-vaapi_device" in args
        cv_idx = args.index("-c:v")
        assert args[cv_idx + 1] == "h264_vaapi"
        assert "-qp" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_videotoolbox_encoder_quality_flag(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "convert", "hwaccel", "in.mp4", "out.mp4",
                "--encoder", "videotoolbox", "--quality", "80",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        cv_idx = args.index("-c:v")
        assert args[cv_idx + 1] == "h264_videotoolbox"
        assert "-q:v" in args
        qv_idx = args.index("-q:v")
        assert args[qv_idx + 1] == "80"


@pytest.mark.command_graph
class TestExtractSprite:
    """extract sprite — fps interval, scale, tile filter, -frames:v 1."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_tile_filter_chain(self, mock_which, mock_run):
        probe_response = _make_run(stdout='{"format":{"duration":"100.0"},"streams":[]}')
        ffmpeg_response = _make_run()
        mock_run.side_effect = [probe_response, ffmpeg_response]
        result = runner.invoke(
            app,
            [
                "extract", "sprite", "in.mp4", "sprite.jpg",
                "--cols", "10", "--rows", "10", "--thumb-width", "160",
            ],
        )
        assert result.exit_code == 0, result.output
        # Last call is the ffmpeg run
        ffmpeg_args = mock_run.call_args[0][0]
        assert "-vf" in ffmpeg_args
        vf_idx = ffmpeg_args.index("-vf")
        vf = ffmpeg_args[vf_idx + 1]
        assert "fps=" in vf
        assert "scale=160" in vf
        assert "tile=10x10" in vf

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_frames_v_1_flag(self, mock_which, mock_run):
        probe_response = _make_run(stdout='{"format":{"duration":"60.0"},"streams":[]}')
        ffmpeg_response = _make_run()
        mock_run.side_effect = [probe_response, ffmpeg_response]
        result = runner.invoke(
            app, ["extract", "sprite", "in.mp4", "sprite.jpg"]
        )
        assert result.exit_code == 0, result.output
        ffmpeg_args = mock_run.call_args[0][0]
        assert "-frames:v" in ffmpeg_args
        fv_idx = ffmpeg_args.index("-frames:v")
        assert ffmpeg_args[fv_idx + 1] == "1"


@pytest.mark.command_graph
class TestTransformSpeed:
    """transform speed — setpts filter, atempo chain, --no-audio."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_2x_speed_setpts_and_atempo(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "speed", "in.mp4", "out.mp4", "--factor", "2.0"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-vf" in args
        vf_idx = args.index("-vf")
        assert "setpts=0.5*PTS" in args[vf_idx + 1]
        assert "-af" in args
        af_idx = args.index("-af")
        assert "atempo=2.0" in args[af_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_no_audio_drops_af(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "speed", "in.mp4", "out.mp4", "--factor", "2.0", "--no-audio"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-an" in args
        assert "-af" not in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_slow_motion_setpts_above_1(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["transform", "speed", "in.mp4", "out.mp4", "--factor", "0.5"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        assert "setpts=2.0*PTS" in args[vf_idx + 1]
        af_idx = args.index("-af")
        assert "atempo=0.5" in args[af_idx + 1]


@pytest.mark.command_graph
class TestTransformWatermark:
    """transform watermark — overlay position, --opacity, --scale."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_default_br_position(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "transform", "watermark", "in.mp4", "out.mp4",
                "--logo", "logo.png",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-filter_complex" in args
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "overlay=W-w-10:H-h-10" in fc

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_opacity_adds_colorchannelmixer(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "transform", "watermark", "in.mp4", "out.mp4",
                "--logo", "logo.png", "--opacity", "0.5",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "colorchannelmixer=aa=0.5" in fc

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_scale_adds_scale_filter(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "transform", "watermark", "in.mp4", "out.mp4",
                "--logo", "logo.png", "--scale", "200",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "scale=200:-1" in fc


@pytest.mark.command_graph
class TestTransformSubtitles:
    """transform subtitles — subtitles= filter, force_style for font-size."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_subtitles_filter_present(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "transform", "subtitles", "in.mp4", "out.mp4",
                "--srt", "subs.srt",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-vf" in args
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert "subtitles=" in vf

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_font_size_adds_force_style(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "transform", "subtitles", "in.mp4", "out.mp4",
                "--srt", "subs.srt", "--font-size", "24",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert "force_style=" in vf
        assert "FontSize=24" in vf


@pytest.mark.command_graph
class TestTransformFade:
    """transform fade — fade=t=in/out in -vf, afade in -af."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_fade_in_vf_and_af(self, mock_which, mock_run):
        probe_response = _make_run(stdout='{"format":{"duration":"30.0"},"streams":[]}')
        ffmpeg_response = _make_run()
        mock_run.side_effect = [probe_response, ffmpeg_response]
        result = runner.invoke(
            app, ["transform", "fade", "in.mp4", "out.mp4", "--fade-in", "2.0"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-vf" in args
        vf_idx = args.index("-vf")
        assert "fade=t=in" in args[vf_idx + 1]
        assert "-af" in args
        af_idx = args.index("-af")
        assert "afade=t=in" in args[af_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_fade_out_vf_and_af(self, mock_which, mock_run):
        probe_response = _make_run(stdout='{"format":{"duration":"30.0"},"streams":[]}')
        ffmpeg_response = _make_run()
        mock_run.side_effect = [probe_response, ffmpeg_response]
        result = runner.invoke(
            app, ["transform", "fade", "in.mp4", "out.mp4", "--fade-out", "3.0"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        vf_idx = args.index("-vf")
        assert "fade=t=out" in args[vf_idx + 1]
        af_idx = args.index("-af")
        assert "afade=t=out" in args[af_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_no_fade_args_exits(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(app, ["transform", "fade", "in.mp4", "out.mp4"])
        assert result.exit_code != 0


@pytest.mark.command_graph
class TestAudioDenoise:
    """audio denoise — afftdn (fft) and arnndn (rnn) filters."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_fft_method_uses_afftdn(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["audio", "denoise", "in.wav", "out.wav", "--method", "fft"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_idx = args.index("-af")
        af = args[af_idx + 1]
        assert "afftdn" in af

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_fft_custom_strength(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            ["audio", "denoise", "in.wav", "out.wav", "--method", "fft", "--strength", "20"],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        af_idx = args.index("-af")
        assert "afftdn=nr=20.0" in args[af_idx + 1]

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_rnn_method_uses_arnndn(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "audio", "denoise", "in.wav", "out.wav",
                "--method", "rnn", "--model", "model.rnnn",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        af_idx = args.index("-af")
        af = args[af_idx + 1]
        assert "arnndn" in af
        assert "m=model.rnnn" in af

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_rnn_without_model_exits(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["audio", "denoise", "in.wav", "out.wav", "--method", "rnn"]
        )
        assert result.exit_code != 0


@pytest.mark.command_graph
class TestAudioDuck:
    """audio duck — static (volume + amix) and dynamic (sidechaincompress)."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_static_mode_uses_volume_and_amix(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "audio", "duck", "out.wav",
                "--voice", "voice.wav", "--music", "music.wav",
                "--music-level", "0.2",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-filter_complex" in args
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "volume=0.2" in fc
        assert "amix" in fc

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_dynamic_mode_uses_sidechaincompress(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "audio", "duck", "out.wav",
                "--voice", "voice.wav", "--music", "music.wav",
                "--dynamic",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "sidechaincompress" in fc
        assert "amix" in fc


@pytest.mark.command_graph
class TestCombineComposite:
    """combine composite — pip, side-by-side, grid layouts."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_pip_layout(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "combine", "composite", "out.mp4",
                "--inputs", "a.mp4", "--inputs", "b.mp4",
                "--layout", "pip",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-filter_complex" in args
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "overlay=" in fc
        assert "scale=iw/4" in fc

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_side_by_side_layout(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "combine", "composite", "out.mp4",
                "--inputs", "a.mp4", "--inputs", "b.mp4",
                "--layout", "side-by-side",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "hstack=inputs=2" in fc

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_grid_layout_four_inputs(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "combine", "composite", "out.mp4",
                "--inputs", "a.mp4", "--inputs", "b.mp4",
                "--inputs", "c.mp4", "--inputs", "d.mp4",
                "--layout", "grid",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "hstack" in fc
        assert "vstack" in fc


@pytest.mark.command_graph
class TestStreamHls:
    """stream hls — -f hls, -hls_time, -hls_flags, -var_stream_map."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_hls_format_flags(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "stream", "hls", "in.mp4",
                "--output-dir", str(tmp_path),
                "--segment-duration", "4",
                "--qualities", "720p",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-f" in args
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "hls"
        assert "-hls_time" in args
        ht_idx = args.index("-hls_time")
        assert args[ht_idx + 1] == "4"
        assert "-hls_flags" in args

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_var_stream_map_present(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "stream", "hls", "in.mp4",
                "--output-dir", str(tmp_path),
                "--qualities", "1080p,720p",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-var_stream_map" in args
        vsm_idx = args.index("-var_stream_map")
        vsm = args[vsm_idx + 1]
        assert "1080p" in vsm
        assert "720p" in vsm


@pytest.mark.command_graph
class TestStreamDash:
    """stream dash — -f dash, -seg_duration, -adaptation_sets."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_dash_format_and_seg_duration(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "stream", "dash", "in.mp4",
                "--output-dir", str(tmp_path),
                "--segment-duration", "6",
                "--qualities", "720p",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-f" in args
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "dash"
        assert "-seg_duration" in args
        sd_idx = args.index("-seg_duration")
        assert args[sd_idx + 1] == "6"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_adaptation_sets_present(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "stream", "dash", "in.mp4",
                "--output-dir", str(tmp_path),
                "--qualities", "720p",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-adaptation_sets" in args
        as_idx = args.index("-adaptation_sets")
        adaptation = args[as_idx + 1]
        assert "streams=v" in adaptation
        assert "streams=a" in adaptation


@pytest.mark.command_graph
class TestStreamLadder:
    """stream ladder — split filter and per-quality outputs."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_per_quality_ffmpeg_calls(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "stream", "ladder", "in.mp4",
                "--output-dir", str(tmp_path),
                "--qualities", "720p,480p",
            ],
        )
        assert result.exit_code == 0, result.output
        # One call per quality
        assert mock_run.call_count == 2

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_scale_filter_per_quality(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "stream", "ladder", "in.mp4",
                "--output-dir", str(tmp_path),
                "--qualities", "720p",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-vf" in args
        vf_idx = args.index("-vf")
        assert "scale=1280:720" in args[vf_idx + 1]
        assert "-movflags" in args


@pytest.mark.command_graph
class TestStreamRestream:
    """stream restream — -f tee with [f=flv:onfail=ignore] wrapping each URL."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_tee_muxer_format(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "stream", "restream", "in.mp4",
                "--destinations", "rtmp://a.example/live/key1",
                "--destinations", "rtmp://b.example/live/key2",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-f" in args
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "tee"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_tee_output_contains_onfail_ignore(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "stream", "restream", "in.mp4",
                "--destinations", "rtmp://a.example/live/key1",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        # Last arg is the tee output spec
        tee_spec = args[-1]
        assert "[f=flv:onfail=ignore]" in tee_spec
        assert "rtmp://a.example/live/key1" in tee_spec


@pytest.mark.command_graph
class TestStreamFakeLive:
    """stream fake-live — -re before -i, -f flv to URL."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_re_flag_before_input(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "stream", "fake-live", "in.mp4",
                "--url", "rtmp://live.example/stream/key",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-re" in args
        re_idx = args.index("-re")
        i_idx = args.index("-i")
        assert re_idx < i_idx

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_flv_format_and_rtmp_url(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        rtmp_url = "rtmp://live.example/stream/key"
        result = runner.invoke(
            app,
            [
                "stream", "fake-live", "in.mp4",
                "--url", rtmp_url,
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-f" in args
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "flv"
        assert args[-1] == rtmp_url


@pytest.mark.command_graph
class TestUtilBatch:
    """util batch — directory walking and per-file ffmpeg calls."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_processes_video_files(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        # Create fake input files
        in_dir = tmp_path / "input"
        out_dir = tmp_path / "output"
        in_dir.mkdir()
        (in_dir / "clip1.mp4").write_bytes(b"")
        (in_dir / "clip2.mkv").write_bytes(b"")
        (in_dir / "readme.txt").write_bytes(b"")  # should be skipped
        result = runner.invoke(
            app,
            [
                "util", "batch",
                "--input-dir", str(in_dir),
                "--output-dir", str(out_dir),
            ],
        )
        assert result.exit_code == 0, result.output
        # Two video files → two ffmpeg calls
        assert mock_run.call_count == 2

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_per_file_uses_libx264(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        in_dir = tmp_path / "input"
        out_dir = tmp_path / "output"
        in_dir.mkdir()
        (in_dir / "clip.mp4").write_bytes(b"")
        result = runner.invoke(
            app,
            [
                "util", "batch",
                "--input-dir", str(in_dir),
                "--output-dir", str(out_dir),
                "--crf", "28",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-c:v" in args
        cv_idx = args.index("-c:v")
        assert args[cv_idx + 1] == "libx264"
        assert "-crf" in args
        crf_idx = args.index("-crf")
        assert args[crf_idx + 1] == "28"


@pytest.mark.command_graph
class TestUtilRecord:
    """util record — platform-specific input device detection."""

    @patch("ffmpeg_cli.sys.platform", "win32")
    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_windows_uses_gdigrab(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["util", "record", "--output", "out.mp4"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-f" in args
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "gdigrab"
        assert "desktop" in args

    @patch("ffmpeg_cli.sys.platform", "linux")
    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_linux_uses_x11grab(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["util", "record", "--output", "out.mp4"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "x11grab"

    @patch("ffmpeg_cli.sys.platform", "darwin")
    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_macos_uses_avfoundation(self, mock_which, mock_run):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app, ["util", "record", "--output", "out.mp4"]
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "avfoundation"


@pytest.mark.command_graph
class TestUtilSurveillance:
    """util surveillance — -rtsp_transport tcp, -f segment, -strftime 1."""

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_rtsp_transport_tcp(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "util", "surveillance",
                "--url", "rtsp://cam.local/stream",
                "--output-dir", str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-rtsp_transport" in args
        rt_idx = args.index("-rtsp_transport")
        assert args[rt_idx + 1] == "tcp"

    @patch("ffmpeg_cli.subprocess.run")
    @patch("ffmpeg_cli.shutil.which", side_effect=_which_side_effect)
    def test_segment_format_and_strftime(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = _make_run()
        result = runner.invoke(
            app,
            [
                "util", "surveillance",
                "--url", "rtsp://cam.local/stream",
                "--output-dir", str(tmp_path),
                "--segment-time", "300",
            ],
        )
        assert result.exit_code == 0, result.output
        args = mock_run.call_args[0][0]
        assert "-f" in args
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "segment"
        assert "-segment_time" in args
        st_idx = args.index("-segment_time")
        assert args[st_idx + 1] == "300"
        assert "-strftime" in args
        sf_idx = args.index("-strftime")
        assert args[sf_idx + 1] == "1"
