"""Tier 1: Typer CLI surface tests — exercises the command entry points.

These tests cover the Typer command graph (help text, argument parsing,
exit codes, --format dispatch) by mocking pyannote_cli.backend's
load_pipeline / load_inference. No real models are loaded, no HF token
required. The single end-to-end path is `info`, which uses the existing
fixtures/test_audio.wav and exercises the real pyannote.audio.Audio loader.

Marker rationale: these are command-graph tests in spirit — they test how
the CLI wires arguments through to logic — so they reuse the existing
`command_graph` marker rather than introducing a new one.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from typer.testing import CliRunner

from pyannote_cli import app


FIXTURES = Path(__file__).parent / "fixtures"
TEST_AUDIO = FIXTURES / "test_audio.wav"


# ---------------------------------------------------------------------------
# Fakes — mirror shapes used in test_commands.py
# ---------------------------------------------------------------------------


class FakeSegment:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


class FakeAnnotation:
    def __init__(self, tracks):
        self._tracks = tracks  # list of (FakeSegment, track_id, label)

    def itertracks(self, yield_label=False):
        if yield_label:
            return iter(self._tracks)
        return iter([(s, t) for s, t, _ in self._tracks])


class FakeDiarizeOutput:
    def __init__(self, tracks):
        self.speaker_diarization = FakeAnnotation(tracks)
        self.exclusive_speaker_diarization = FakeAnnotation(tracks)
        self.speaker_embeddings = None

    def serialize(self):
        entries = [
            {"start": seg.start, "end": seg.end, "speaker": label}
            for seg, _, label in self.speaker_diarization.itertracks(yield_label=True)
        ]
        return {"diarization": entries, "exclusive_diarization": entries}


def _sample_tracks():
    return [
        (FakeSegment(0.5, 1.7), "A", "SPEAKER_00"),
        (FakeSegment(1.8, 3.5), "B", "SPEAKER_01"),
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def audio_file(tmp_path) -> Path:
    """A tiny non-empty file path that .exists() returns True for."""
    f = tmp_path / "input.wav"
    f.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfake")
    return f


@pytest.fixture
def fake_pipeline():
    """A MagicMock that, when called, returns a FakeDiarizeOutput."""
    pipeline = MagicMock()
    pipeline.return_value = FakeDiarizeOutput(_sample_tracks())
    return pipeline


@pytest.fixture
def fake_inference():
    """A MagicMock that, when called, returns a deterministic embedding."""
    inference = MagicMock()
    inference.return_value = np.array([0.1, 0.2, 0.3, 0.4])
    return inference


# ===========================================================================
# 1. Top-level --help
# ===========================================================================


@pytest.mark.command_graph
class TestRootHelp:
    def test_help_exits_zero(self, runner):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_lists_subcommands(self, runner):
        result = runner.invoke(app, ["--help"])
        out = result.output
        for cmd in ("diarize", "vad", "embed", "verify", "info"):
            assert cmd in out, f"{cmd!r} missing from --help output"

    def test_no_args_shows_help(self, runner):
        # app was created with no_args_is_help=True
        result = runner.invoke(app, [])
        # Typer exits 0 or 2 for help-on-no-args depending on version;
        # accept either, but output must mention usage.
        assert "Usage" in result.output or "usage" in result.output


# ===========================================================================
# 2. Per-subcommand --help
# ===========================================================================


@pytest.mark.command_graph
class TestSubcommandHelp:
    @pytest.mark.parametrize("cmd", ["diarize", "vad", "embed", "verify", "info"])
    def test_subcommand_help_exits_zero(self, runner, cmd):
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0, result.output

    def test_diarize_help_mentions_key_flags(self, runner):
        result = runner.invoke(app, ["diarize", "--help"])
        out = result.output
        assert "--format" in out
        assert "--output" in out
        # speaker-count flags
        assert "speakers" in out

    def test_vad_help_mentions_format(self, runner):
        result = runner.invoke(app, ["vad", "--help"])
        assert "--format" in result.output

    def test_embed_help_mentions_model(self, runner):
        result = runner.invoke(app, ["embed", "--help"])
        assert "--model" in result.output

    def test_verify_help_mentions_threshold(self, runner):
        result = runner.invoke(app, ["verify", "--help"])
        assert "--threshold" in result.output


# ===========================================================================
# 3. Argument parsing — invalid input
# ===========================================================================


@pytest.mark.command_graph
class TestArgumentParsing:
    @pytest.mark.parametrize("cmd", ["diarize", "vad", "embed", "info"])
    def test_missing_file_arg(self, runner, cmd):
        result = runner.invoke(app, [cmd])
        # Typer/Click exits 2 for usage errors
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "FILE" in result.output

    def test_verify_requires_two_files(self, runner):
        result = runner.invoke(app, ["verify"])
        assert result.exit_code != 0
        # Should complain about missing file_a
        assert "Missing argument" in result.output or "FILE" in result.output.upper()

    def test_verify_one_file_still_errors(self, runner, audio_file):
        result = runner.invoke(app, ["verify", str(audio_file)])
        assert result.exit_code != 0

    def test_unknown_subcommand(self, runner):
        result = runner.invoke(app, ["bogus-command"])
        assert result.exit_code != 0

    def test_diarize_bad_format_value(self, runner, audio_file):
        with patch("pyannote_cli.diarize.load_pipeline") as lp:
            lp.return_value = MagicMock(return_value=FakeDiarizeOutput(_sample_tracks()))
            result = runner.invoke(
                app, ["diarize", str(audio_file), "--format", "bogus"]
            )
        assert result.exit_code != 0
        assert "Unknown format" in result.output

    def test_vad_bad_format_value(self, runner, audio_file):
        with patch("pyannote_cli.vad.load_pipeline") as lp:
            # vad calls run_vad which collapses_to_speech — needs real Annotation.
            # Returning the FakeAnnotation directly bypasses that path because
            # run_vad reaches into output.speaker_diarization. Patch run_vad too.
            lp.return_value = MagicMock()
            with patch("pyannote_cli.vad.run_vad", return_value=FakeAnnotation(_sample_tracks())):
                result = runner.invoke(
                    app, ["vad", str(audio_file), "--format", "bogus"]
                )
        assert result.exit_code != 0
        assert "Unknown format" in result.output

    def test_embed_bad_model_value(self, runner, audio_file):
        # Bad --model is rejected before load_inference is called.
        result = runner.invoke(app, ["embed", str(audio_file), "--model", "nope"])
        assert result.exit_code != 0
        assert "Unknown model" in result.output

    def test_verify_bad_model_value(self, runner, audio_file):
        result = runner.invoke(
            app, ["verify", str(audio_file), str(audio_file), "--model", "nope"]
        )
        assert result.exit_code != 0
        assert "Unknown model" in result.output


# ===========================================================================
# 4. Exit codes — file not found
# ===========================================================================


@pytest.mark.command_graph
class TestFileNotFound:
    @pytest.mark.parametrize("cmd", ["diarize", "vad", "embed", "info"])
    def test_missing_file_returns_nonzero(self, runner, cmd, tmp_path):
        ghost = tmp_path / "does_not_exist.wav"
        result = runner.invoke(app, [cmd, str(ghost)])
        assert result.exit_code != 0
        assert "File not found" in result.output

    def test_verify_missing_first_file(self, runner, tmp_path, audio_file):
        ghost = tmp_path / "ghost.wav"
        result = runner.invoke(app, ["verify", str(ghost), str(audio_file)])
        assert result.exit_code != 0
        assert "File not found" in result.output

    def test_verify_missing_second_file(self, runner, tmp_path, audio_file):
        ghost = tmp_path / "ghost.wav"
        result = runner.invoke(app, ["verify", str(audio_file), str(ghost)])
        assert result.exit_code != 0
        assert "File not found" in result.output


# ===========================================================================
# 5. --format dispatch — diarize
# ===========================================================================


@pytest.mark.command_graph
class TestDiarizeFormatDispatch:
    def test_rttm_to_stdout(self, runner, audio_file, fake_pipeline):
        with patch("pyannote_cli.diarize.load_pipeline", return_value=fake_pipeline):
            result = runner.invoke(
                app, ["diarize", str(audio_file), "--format", "rttm"]
            )
        assert result.exit_code == 0, result.output
        assert "SPEAKER" in result.output
        assert "SPEAKER_00" in result.output

    def test_json_to_stdout(self, runner, audio_file, fake_pipeline):
        with patch("pyannote_cli.diarize.load_pipeline", return_value=fake_pipeline):
            result = runner.invoke(
                app, ["diarize", str(audio_file), "--format", "json"]
            )
        assert result.exit_code == 0, result.output
        # Find the JSON payload in output (skip any warnings prefixed lines)
        payload_start = result.output.find("{")
        data = json.loads(result.output[payload_start:])
        assert "diarization" in data

    def test_txt_to_stdout(self, runner, audio_file, fake_pipeline):
        with patch("pyannote_cli.diarize.load_pipeline", return_value=fake_pipeline):
            result = runner.invoke(
                app, ["diarize", str(audio_file), "--format", "txt"]
            )
        assert result.exit_code == 0, result.output
        assert "-->" in result.output  # txt formatter uses --> separator

    def test_output_to_file(self, runner, audio_file, fake_pipeline, tmp_path):
        out_file = tmp_path / "result.rttm"
        with patch("pyannote_cli.diarize.load_pipeline", return_value=fake_pipeline):
            result = runner.invoke(
                app,
                [
                    "diarize",
                    str(audio_file),
                    "--format",
                    "rttm",
                    "--output",
                    str(out_file),
                ],
            )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        assert "SPEAKER_00" in out_file.read_text()
        # CLI should report where it saved
        assert str(out_file) in result.output

    def test_passes_num_speakers(self, runner, audio_file, fake_pipeline):
        with patch("pyannote_cli.diarize.load_pipeline", return_value=fake_pipeline):
            result = runner.invoke(
                app, ["diarize", str(audio_file), "--num-speakers", "3"]
            )
        assert result.exit_code == 0, result.output
        # The pipeline mock should have been called with num_speakers=3
        _, kwargs = fake_pipeline.call_args
        assert kwargs.get("num_speakers") == 3


# ===========================================================================
# 5b. --format dispatch — vad
# ===========================================================================


@pytest.mark.command_graph
class TestVadFormatDispatch:
    def _patches(self, ann):
        # vad's run_vad does Annotation work — patch run_vad to skip it.
        return (
            patch("pyannote_cli.vad.load_pipeline", return_value=MagicMock()),
            patch("pyannote_cli.vad.run_vad", return_value=ann),
        )

    def test_rttm_to_stdout(self, runner, audio_file):
        ann = FakeAnnotation([(FakeSegment(0.0, 1.5), "A", "SPEECH")])
        lp, rv = self._patches(ann)
        with lp, rv:
            result = runner.invoke(app, ["vad", str(audio_file), "--format", "rttm"])
        assert result.exit_code == 0, result.output
        assert "SPEECH" in result.output
        assert "SPEAKER" in result.output

    def test_json_to_stdout(self, runner, audio_file):
        ann = FakeAnnotation([(FakeSegment(0.0, 1.5), "A", "SPEECH")])
        lp, rv = self._patches(ann)
        with lp, rv:
            result = runner.invoke(app, ["vad", str(audio_file), "--format", "json"])
        assert result.exit_code == 0, result.output
        payload_start = result.output.find("{")
        data = json.loads(result.output[payload_start:])
        assert "speech_regions" in data
        assert len(data["speech_regions"]) == 1

    def test_txt_to_stdout(self, runner, audio_file):
        ann = FakeAnnotation([(FakeSegment(0.0, 1.5), "A", "SPEECH")])
        lp, rv = self._patches(ann)
        with lp, rv:
            result = runner.invoke(app, ["vad", str(audio_file), "--format", "txt"])
        assert result.exit_code == 0, result.output
        assert "Total speech:" in result.output

    def test_output_to_file(self, runner, audio_file, tmp_path):
        ann = FakeAnnotation([(FakeSegment(0.0, 1.5), "A", "SPEECH")])
        out_file = tmp_path / "vad.rttm"
        lp, rv = self._patches(ann)
        with lp, rv:
            result = runner.invoke(
                app,
                ["vad", str(audio_file), "--format", "rttm", "--output", str(out_file)],
            )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        assert "SPEECH" in out_file.read_text()


# ===========================================================================
# 5c. --format dispatch — embed
# ===========================================================================


@pytest.mark.command_graph
class TestEmbedFormatDispatch:
    def test_default_json_to_stdout(self, runner, audio_file, fake_inference):
        with patch("pyannote_cli.embed.load_inference", return_value=fake_inference):
            result = runner.invoke(app, ["embed", str(audio_file)])
        assert result.exit_code == 0, result.output
        payload_start = result.output.find("{")
        data = json.loads(result.output[payload_start:])
        assert data["dimension"] == 4
        assert len(data["embedding"]) == 4

    def test_npy_output(self, runner, audio_file, fake_inference, tmp_path):
        out_file = tmp_path / "emb.npy"
        with patch("pyannote_cli.embed.load_inference", return_value=fake_inference):
            result = runner.invoke(
                app, ["embed", str(audio_file), "--output", str(out_file)]
            )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        loaded = np.load(str(out_file))
        assert loaded.shape == (4,)
        assert str(out_file) in result.output

    def test_json_file_output(self, runner, audio_file, fake_inference, tmp_path):
        # Non-.npy --output should write JSON
        out_file = tmp_path / "emb.json"
        with patch("pyannote_cli.embed.load_inference", return_value=fake_inference):
            result = runner.invoke(
                app, ["embed", str(audio_file), "--output", str(out_file)]
            )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["dimension"] == 4

    def test_resnet34_model_selected(self, runner, audio_file, fake_inference):
        with patch(
            "pyannote_cli.embed.load_inference", return_value=fake_inference
        ) as li:
            result = runner.invoke(
                app, ["embed", str(audio_file), "--model", "resnet34"]
            )
        assert result.exit_code == 0, result.output
        # First positional arg is the model name string
        assert li.call_args.args[0] == "pyannote/wespeaker-voxceleb-resnet34-LM"

    def test_embedding_model_selected(self, runner, audio_file, fake_inference):
        with patch(
            "pyannote_cli.embed.load_inference", return_value=fake_inference
        ) as li:
            result = runner.invoke(
                app, ["embed", str(audio_file), "--model", "embedding"]
            )
        assert result.exit_code == 0, result.output
        assert li.call_args.args[0] == "pyannote/embedding"


# ===========================================================================
# 5d. verify command — wiring
# ===========================================================================


@pytest.mark.command_graph
class TestVerifyDispatch:
    def test_same_speaker_output(self, runner, audio_file):
        inference = MagicMock()
        inference.side_effect = [np.array([1.0, 0.0]), np.array([0.95, 0.05])]
        with patch("pyannote_cli.verify.load_inference", return_value=inference):
            result = runner.invoke(
                app, ["verify", str(audio_file), str(audio_file)]
            )
        assert result.exit_code == 0, result.output
        assert "Score:" in result.output
        assert "Threshold:" in result.output
        assert "SAME speaker" in result.output

    def test_different_speakers_output(self, runner, audio_file):
        inference = MagicMock()
        inference.side_effect = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
        with patch("pyannote_cli.verify.load_inference", return_value=inference):
            result = runner.invoke(
                app, ["verify", str(audio_file), str(audio_file)]
            )
        assert result.exit_code == 0, result.output
        assert "DIFFERENT speakers" in result.output

    def test_threshold_propagates(self, runner, audio_file):
        inference = MagicMock()
        # Score will be 1.0 — make threshold 1.5 so it's below.
        inference.side_effect = [np.array([1.0, 0.0]), np.array([1.0, 0.0])]
        with patch("pyannote_cli.verify.load_inference", return_value=inference):
            result = runner.invoke(
                app,
                ["verify", str(audio_file), str(audio_file), "--threshold", "1.5"],
            )
        assert result.exit_code == 0, result.output
        assert "1.5" in result.output  # threshold echoed


# ===========================================================================
# 6. info — end-to-end against the existing fixture
# ===========================================================================


@pytest.mark.command_graph
@pytest.mark.skipif(not TEST_AUDIO.exists(), reason="No test audio fixture")
class TestInfoEndToEnd:
    def test_info_runs_on_real_audio(self, runner):
        result = runner.invoke(app, ["info", str(TEST_AUDIO)])
        assert result.exit_code == 0, result.output
        out = result.output
        assert "Duration:" in out
        assert "Sample rate:" in out
        assert "Channels:" in out

    def test_info_reports_expected_sample_rate(self, runner):
        result = runner.invoke(app, ["info", str(TEST_AUDIO)])
        assert result.exit_code == 0, result.output
        # Fixture is 16 kHz mono per test_integration.py
        assert "16000" in result.output
