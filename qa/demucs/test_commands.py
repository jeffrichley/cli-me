"""Tier 1: Command-graph tests for Demucs CLI commands.

These tests verify that the logic layer builds the correct demucs argument lists.
No binary needed — pure unit tests.
"""

import sys
import pytest

# Add the scripts directory to the path so we can import the commands module
sys.path.insert(
    0,
    str(
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "skill-repo"
        / "demucs"
        / "scripts"
    ),
)

from demucs_cli.commands import separate_audio, list_models


# ─── separate_audio ─────────────────────────────────────────────────────────


@pytest.mark.command_graph
class TestSeparateAudioDefaults:
    FILE = "song.mp3"

    def test_empty_files_raises(self):
        with pytest.raises(ValueError, match="No input files"):
            separate_audio.build_args([])

    def test_default_args_include_file(self):
        args = separate_audio.build_args([self.FILE])
        assert args[-1] == self.FILE

    def test_default_model_is_htdemucs(self):
        args = separate_audio.build_args([self.FILE])
        assert "-n" in args
        idx = args.index("-n")
        assert args[idx + 1] == "htdemucs"

    def test_default_device_is_auto(self):
        """When device is None (auto), no -d flag should be present."""
        args = separate_audio.build_args([self.FILE])
        assert "-d" not in args

    def test_default_shifts_is_1(self):
        args = separate_audio.build_args([self.FILE])
        assert "--shifts" in args
        idx = args.index("--shifts")
        assert args[idx + 1] == "1"

    def test_default_output_dir(self):
        args = separate_audio.build_args([self.FILE])
        assert "-o" in args
        idx = args.index("-o")
        assert args[idx + 1] == "separated"


@pytest.mark.command_graph
class TestSeparateAudioModel:
    FILE = "song.mp3"

    def test_custom_model(self):
        args = separate_audio.build_args([self.FILE], model="htdemucs_ft")
        idx = args.index("-n")
        assert args[idx + 1] == "htdemucs_ft"

    def test_custom_repo(self):
        args = separate_audio.build_args(
            [self.FILE], model="my_model", repo="/models"
        )
        assert "--repo" in args
        idx = args.index("--repo")
        assert args[idx + 1] == "/models"


@pytest.mark.command_graph
class TestSeparateAudioDevice:
    FILE = "song.mp3"

    def test_explicit_cpu(self):
        args = separate_audio.build_args([self.FILE], device="cpu")
        assert "-d" in args
        idx = args.index("-d")
        assert args[idx + 1] == "cpu"

    def test_explicit_cuda(self):
        args = separate_audio.build_args([self.FILE], device="cuda")
        idx = args.index("-d")
        assert args[idx + 1] == "cuda"

    def test_explicit_cuda_index(self):
        args = separate_audio.build_args([self.FILE], device="cuda:1")
        idx = args.index("-d")
        assert args[idx + 1] == "cuda:1"

    def test_jobs_on_cpu(self):
        args = separate_audio.build_args([self.FILE], device="cpu", jobs=4)
        assert "-j" in args
        idx = args.index("-j")
        assert args[idx + 1] == "4"

    def test_jobs_default_not_present(self):
        args = separate_audio.build_args([self.FILE])
        assert "-j" not in args


@pytest.mark.command_graph
class TestSeparateAudioStems:
    FILE = "song.mp3"

    def test_two_stems_vocals(self):
        args = separate_audio.build_args([self.FILE], two_stems="vocals")
        assert "--two-stems" in args
        idx = args.index("--two-stems")
        assert args[idx + 1] == "vocals"

    def test_two_stems_drums(self):
        args = separate_audio.build_args([self.FILE], two_stems="drums")
        idx = args.index("--two-stems")
        assert args[idx + 1] == "drums"

    def test_no_other_method_flag(self):
        """--other-method is not in demucs 4.0.1 (unreleased feature)."""
        args = separate_audio.build_args([self.FILE], two_stems="vocals")
        assert "--other-method" not in args


@pytest.mark.command_graph
class TestSeparateAudioFormat:
    FILE = "song.mp3"

    def test_mp3_output(self):
        args = separate_audio.build_args([self.FILE], format="mp3")
        assert "--mp3" in args
        assert "--flac" not in args

    def test_flac_output(self):
        args = separate_audio.build_args([self.FILE], format="flac")
        assert "--flac" in args
        assert "--mp3" not in args

    def test_wav_output_default(self):
        args = separate_audio.build_args([self.FILE])
        assert "--mp3" not in args
        assert "--flac" not in args

    def test_mp3_bitrate(self):
        args = separate_audio.build_args(
            [self.FILE], format="mp3", mp3_bitrate=192
        )
        assert "--mp3-bitrate" in args
        idx = args.index("--mp3-bitrate")
        assert args[idx + 1] == "192"

    def test_mp3_preset(self):
        args = separate_audio.build_args(
            [self.FILE], format="mp3", mp3_preset=5
        )
        assert "--mp3-preset" in args
        idx = args.index("--mp3-preset")
        assert args[idx + 1] == "5"

    def test_int24(self):
        args = separate_audio.build_args([self.FILE], int24=True)
        assert "--int24" in args
        assert "--float32" not in args

    def test_float32(self):
        args = separate_audio.build_args([self.FILE], float32=True)
        assert "--float32" in args
        assert "--int24" not in args

    def test_int24_takes_precedence_over_float32(self):
        """When both are True, int24 wins (if/elif precedence)."""
        args = separate_audio.build_args([self.FILE], int24=True, float32=True)
        assert "--int24" in args
        assert "--float32" not in args

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Unknown format"):
            separate_audio.build_args([self.FILE], format="ogg")

    def test_wav_explicit_format_is_noop(self):
        """format='wav' produces same output as format=None (no format flags)."""
        args_default = separate_audio.build_args([self.FILE])
        args_wav = separate_audio.build_args([self.FILE], format="wav")
        assert args_default == args_wav

    def test_mp3_bitrate_ignored_without_mp3_format(self):
        """mp3_bitrate is only emitted when format is mp3."""
        args = separate_audio.build_args([self.FILE], mp3_bitrate=192)
        assert "--mp3-bitrate" not in args

    def test_mp3_preset_ignored_without_mp3_format(self):
        """mp3_preset is only emitted when format is mp3."""
        args = separate_audio.build_args([self.FILE], mp3_preset=5)
        assert "--mp3-preset" not in args


@pytest.mark.command_graph
class TestSeparateAudioProcessing:
    FILE = "song.mp3"

    def test_custom_shifts(self):
        args = separate_audio.build_args([self.FILE], shifts=5)
        idx = args.index("--shifts")
        assert args[idx + 1] == "5"

    def test_custom_overlap(self):
        args = separate_audio.build_args([self.FILE], overlap=0.5)
        assert "--overlap" in args
        idx = args.index("--overlap")
        assert args[idx + 1] == "0.5"

    def test_segment(self):
        args = separate_audio.build_args([self.FILE], segment=8)
        assert "--segment" in args
        idx = args.index("--segment")
        assert args[idx + 1] == "8"

    def test_no_split(self):
        args = separate_audio.build_args([self.FILE], no_split=True)
        assert "--no-split" in args

    def test_clip_mode(self):
        args = separate_audio.build_args([self.FILE], clip_mode="clamp")
        assert "--clip-mode" in args
        idx = args.index("--clip-mode")
        assert args[idx + 1] == "clamp"

    def test_clip_mode_rescale(self):
        args = separate_audio.build_args([self.FILE], clip_mode="rescale")
        idx = args.index("--clip-mode")
        assert args[idx + 1] == "rescale"

    def test_invalid_clip_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown clip_mode"):
            separate_audio.build_args([self.FILE], clip_mode="banana")

    def test_clip_mode_none_rejected(self):
        """'none' is not valid in demucs 4.0.1 (only rescale, clamp)."""
        with pytest.raises(ValueError, match="Unknown clip_mode"):
            separate_audio.build_args([self.FILE], clip_mode="none")

    def test_custom_output(self):
        args = separate_audio.build_args([self.FILE], output="/tmp/stems")
        idx = args.index("-o")
        assert args[idx + 1] == "/tmp/stems"

    def test_multiple_files(self):
        files = ["song1.mp3", "song2.wav", "song3.flac"]
        args = separate_audio.build_args(files)
        # Files must be at the END of the arg list (demucs requirement)
        assert args[-len(files):] == files

    def test_verbose(self):
        args = separate_audio.build_args([self.FILE], verbose=True)
        assert "-v" in args

    def test_verbose_false_default(self):
        args = separate_audio.build_args([self.FILE])
        assert "-v" not in args

    def test_shifts_zero(self):
        args = separate_audio.build_args([self.FILE], shifts=0)
        idx = args.index("--shifts")
        assert args[idx + 1] == "0"


# ─── list_models ─────────────────────────────────────────────────────────────


@pytest.mark.command_graph
class TestListModels:
    def test_model_descriptions_include_default(self):
        """The MODEL_DESCRIPTIONS dict includes htdemucs (the default model)."""
        assert "htdemucs" in list_models.MODEL_DESCRIPTIONS
        assert "htdemucs_ft" in list_models.MODEL_DESCRIPTIONS

    def test_build_output_no_models(self):
        """Fallback message when no models are found."""
        import unittest.mock as mock
        with mock.patch.object(list_models, "find_model_configs", return_value=[]):
            output = list_models.build_output()
        assert "No models found" in output

    def test_build_output_with_models(self):
        """Formatted output includes model names and descriptions."""
        import unittest.mock as mock
        with mock.patch.object(
            list_models, "find_model_configs", return_value=["htdemucs", "mdx"]
        ):
            output = list_models.build_output()
        assert "htdemucs" in output
        assert "mdx" in output
        assert "Available Demucs models" in output
        # Verify descriptions are included, not just names
        assert "Hybrid Transformer" in output  # htdemucs description
        assert "MDX challenge" in output  # mdx description

    def test_build_output_unknown_model(self):
        """Models not in MODEL_DESCRIPTIONS appear without description."""
        import unittest.mock as mock
        with mock.patch.object(
            list_models, "find_model_configs",
            return_value=["htdemucs", "custom_experiment"],
        ):
            output = list_models.build_output()
        assert "custom_experiment" in output
        assert "htdemucs" in output


# ─── separate_audio: structural assertions ───────────────────────────────────


@pytest.mark.command_graph
class TestSeparateAudioStructural:
    FILE = "song.mp3"

    def test_no_spurious_flags(self):
        """Default args contain only expected flags — no extra garbage."""
        args = separate_audio.build_args([self.FILE])
        # Every element should be a known flag, a value, or the file
        known_flags = {
            "-n", "--shifts", "-o", "-v", "-d", "-j",
            "--repo", "--overlap", "--segment", "--no-split",
            "--two-stems", "--mp3", "--flac",
            "--mp3-bitrate", "--mp3-preset",
            "--int24", "--float32", "--clip-mode",
        }
        for i, arg in enumerate(args):
            if arg.startswith("-"):
                assert arg in known_flags, f"Unexpected flag at index {i}: {arg}"

    def test_int24_ignored_with_mp3(self):
        """--int24 is not emitted when format is mp3."""
        args = separate_audio.build_args([self.FILE], format="mp3", int24=True)
        assert "--mp3" in args
        assert "--int24" not in args

    def test_float32_ignored_with_flac(self):
        """--float32 is not emitted when format is flac."""
        args = separate_audio.build_args([self.FILE], format="flac", float32=True)
        assert "--flac" in args
        assert "--float32" not in args


@pytest.mark.command_graph
class TestSeparateAudioBoundaryValues:
    FILE = "song.mp3"

    def test_shifts_negative(self):
        """Negative shifts are passed through (demucs validates)."""
        args = separate_audio.build_args([self.FILE], shifts=-1)
        idx = args.index("--shifts")
        assert args[idx + 1] == "-1"

    def test_overlap_zero(self):
        """overlap=0.0 is passed through (not treated as falsy)."""
        args = separate_audio.build_args([self.FILE], overlap=0.0)
        assert "--overlap" in args
        idx = args.index("--overlap")
        assert args[idx + 1] == "0.0"

    def test_segment_zero(self):
        args = separate_audio.build_args([self.FILE], segment=0)
        idx = args.index("--segment")
        assert args[idx + 1] == "0"

    def test_jobs_zero(self):
        args = separate_audio.build_args([self.FILE], jobs=0)
        assert "-j" in args
        idx = args.index("-j")
        assert args[idx + 1] == "0"

    def test_mp3_bitrate_zero(self):
        args = separate_audio.build_args([self.FILE], format="mp3", mp3_bitrate=0)
        idx = args.index("--mp3-bitrate")
        assert args[idx + 1] == "0"


@pytest.mark.command_graph
class TestSeparateAudioCombination:
    """Kitchen-sink test: many params at once to catch interaction bugs."""

    def test_full_combination(self):
        files = ["song1.mp3", "song2.wav"]
        args = separate_audio.build_args(
            files,
            model="htdemucs_ft",
            repo="/models",
            device="cuda",
            shifts=3,
            overlap=0.1,
            segment=5,
            two_stems="vocals",
            format="mp3",
            mp3_bitrate=192,
            mp3_preset=5,
            clip_mode="clamp",
            output="/tmp/out",
            jobs=2,
            verbose=True,
        )
        # Files at end
        assert args[-2:] == files
        # Key flags present with correct values
        assert args[args.index("-n") + 1] == "htdemucs_ft"
        assert args[args.index("--repo") + 1] == "/models"
        assert args[args.index("-d") + 1] == "cuda"
        assert args[args.index("--shifts") + 1] == "3"
        assert args[args.index("--overlap") + 1] == "0.1"
        assert args[args.index("--segment") + 1] == "5"
        assert args[args.index("--two-stems") + 1] == "vocals"
        assert "--mp3" in args
        assert args[args.index("--mp3-bitrate") + 1] == "192"
        assert args[args.index("--mp3-preset") + 1] == "5"
        assert args[args.index("--clip-mode") + 1] == "clamp"
        assert args[args.index("-o") + 1] == "/tmp/out"
        assert args[args.index("-j") + 1] == "2"
        assert "-v" in args
        # int24/float32 should NOT be present (format is mp3)
        assert "--int24" not in args
        assert "--float32" not in args


@pytest.mark.command_graph
class TestSeparateAudioTruthiness:
    """Empty strings behave like None for optional string params."""
    FILE = "song.mp3"

    def test_repo_empty_string_omitted(self):
        args = separate_audio.build_args([self.FILE], repo="")
        assert "--repo" not in args

    def test_two_stems_empty_string_omitted(self):
        args = separate_audio.build_args([self.FILE], two_stems="")
        assert "--two-stems" not in args

    def test_output_empty_string_uses_default(self):
        args = separate_audio.build_args([self.FILE], output="")
        idx = args.index("-o")
        assert args[idx + 1] == "separated"
