"""Tier 1: Command logic tests — mock pipeline, no real model needed."""

import json
import pytest
from unittest.mock import MagicMock
from pathlib import Path

from pyannote_cli.commands.diarize import run_diarize, format_rttm, format_json, format_txt


class FakeSegment:
    def __init__(self, start, end):
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
        entries = []
        for seg, _, label in self.speaker_diarization.itertracks(yield_label=True):
            entries.append({"start": seg.start, "end": seg.end, "speaker": label})
        return {
            "diarization": entries,
            "exclusive_diarization": entries,
        }


@pytest.fixture
def sample_output():
    tracks = [
        (FakeSegment(0.5, 1.7), "A", "SPEAKER_00"),
        (FakeSegment(1.8, 3.5), "B", "SPEAKER_01"),
        (FakeSegment(3.6, 5.0), "A", "SPEAKER_00"),
    ]
    return FakeDiarizeOutput(tracks)


@pytest.fixture
def mock_pipeline(sample_output):
    pipeline = MagicMock()
    pipeline.return_value = sample_output
    return pipeline


@pytest.mark.command_graph
class TestRunDiarize:
    def test_calls_pipeline_with_file(self, mock_pipeline):
        run_diarize(mock_pipeline, Path("test.wav"))
        mock_pipeline.assert_called_once_with("test.wav")

    def test_passes_num_speakers(self, mock_pipeline):
        run_diarize(mock_pipeline, Path("test.wav"), num_speakers=3)
        mock_pipeline.assert_called_once_with("test.wav", num_speakers=3)

    def test_passes_min_max_speakers(self, mock_pipeline):
        run_diarize(mock_pipeline, Path("test.wav"), min_speakers=2, max_speakers=5)
        mock_pipeline.assert_called_once_with("test.wav", min_speakers=2, max_speakers=5)

    def test_returns_pipeline_output(self, mock_pipeline, sample_output):
        result = run_diarize(mock_pipeline, Path("test.wav"))
        assert result is sample_output


@pytest.mark.command_graph
class TestFormatRttm:
    def test_produces_rttm_lines(self, sample_output):
        rttm = format_rttm(sample_output, filename="test")
        lines = rttm.strip().split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("SPEAKER test 1")
        assert "SPEAKER_00" in lines[0]

    def test_rttm_uses_duration_not_end(self, sample_output):
        rttm = format_rttm(sample_output)
        first_line = rttm.split("\n")[0]
        # First segment: start=0.5, end=1.7, duration=1.2
        assert "0.500" in first_line
        assert "1.200" in first_line


@pytest.mark.command_graph
class TestFormatJson:
    def test_produces_valid_json(self, sample_output):
        result = format_json(sample_output)
        data = json.loads(result)
        assert "diarization" in data
        assert "exclusive_diarization" in data

    def test_json_has_correct_entries(self, sample_output):
        data = json.loads(format_json(sample_output))
        entries = data["diarization"]
        assert len(entries) == 3
        assert entries[0]["speaker"] == "SPEAKER_00"
        assert entries[0]["start"] == 0.5
        assert entries[0]["end"] == 1.7


@pytest.mark.command_graph
class TestFormatTxt:
    def test_produces_readable_lines(self, sample_output):
        txt = format_txt(sample_output)
        lines = txt.strip().split("\n")
        assert len(lines) == 3
        assert "SPEAKER_00" in lines[0]
        assert "-->" in lines[0]
