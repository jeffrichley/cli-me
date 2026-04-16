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


from pyannote_cli.commands.vad import run_vad, format_rttm as vad_format_rttm, format_json as vad_format_json, format_txt as vad_format_txt


@pytest.fixture
def vad_output():
    tracks = [
        (FakeSegment(0.5, 2.0), "A", "SPEECH"),
        (FakeSegment(3.0, 5.5), "B", "SPEECH"),
        (FakeSegment(7.0, 8.0), "C", "SPEECH"),
    ]
    return FakeAnnotation(tracks)


@pytest.fixture
def mock_vad_pipeline(vad_output):
    pipeline = MagicMock()
    pipeline.return_value = vad_output
    return pipeline


@pytest.mark.command_graph
class TestRunVad:
    def test_calls_pipeline(self, mock_vad_pipeline):
        run_vad(mock_vad_pipeline, Path("test.wav"))
        mock_vad_pipeline.assert_called_once_with("test.wav")

    def test_returns_annotation(self, mock_vad_pipeline, vad_output):
        result = run_vad(mock_vad_pipeline, Path("test.wav"))
        assert result is vad_output


@pytest.mark.command_graph
class TestVadFormatRttm:
    def test_produces_speech_labels(self, vad_output):
        rttm = vad_format_rttm(vad_output)
        assert "SPEECH" in rttm
        assert rttm.count("\n") == 2  # 3 lines


@pytest.mark.command_graph
class TestVadFormatJson:
    def test_produces_valid_json(self, vad_output):
        data = json.loads(vad_format_json(vad_output))
        assert "speech_regions" in data
        assert len(data["speech_regions"]) == 3


@pytest.mark.command_graph
class TestVadFormatTxt:
    def test_includes_total_speech(self, vad_output):
        txt = vad_format_txt(vad_output)
        assert "Total speech:" in txt


import numpy as np
from pyannote_cli.commands.verify import extract_embedding, cosine_similarity, verify_speakers


@pytest.mark.command_graph
class TestExtractEmbedding:
    def test_normalizes_embedding(self):
        inference = MagicMock()
        inference.return_value = np.array([3.0, 4.0])
        emb = extract_embedding(inference, Path("test.wav"))
        assert np.allclose(np.linalg.norm(emb), 1.0)

    def test_calls_inference_with_file(self):
        inference = MagicMock()
        inference.return_value = np.array([1.0, 0.0])
        extract_embedding(inference, Path("test.wav"))
        inference.assert_called_once_with("test.wav")


@pytest.mark.command_graph
class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = np.array([1.0, 0.0])
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        assert cosine_similarity(a, b) == 0.0


@pytest.mark.command_graph
class TestVerifySpeakers:
    def test_same_speaker(self):
        inference = MagicMock()
        inference.side_effect = [np.array([1.0, 0.0]), np.array([0.95, 0.05])]
        result = verify_speakers(inference, Path("a.wav"), Path("b.wav"), threshold=0.7)
        assert result["same_speaker"] is True
        assert result["score"] > 0.7

    def test_different_speakers(self):
        inference = MagicMock()
        inference.side_effect = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
        result = verify_speakers(inference, Path("a.wav"), Path("b.wav"), threshold=0.7)
        assert result["same_speaker"] is False
        assert result["score"] < 0.7


from pyannote_cli.commands.embed import run_embed, format_json as embed_format_json


@pytest.mark.command_graph
class TestRunEmbed:
    def test_calls_inference(self):
        inference = MagicMock()
        inference.return_value = np.array([1.0, 2.0, 3.0])
        run_embed(inference, Path("test.wav"))
        inference.assert_called_once_with("test.wav")

    def test_squeezes_2d_to_1d(self):
        inference = MagicMock()
        inference.return_value = np.array([[1.0, 2.0, 3.0]])
        result = run_embed(inference, Path("test.wav"))
        assert result.ndim == 1
        assert len(result) == 3

    def test_keeps_1d(self):
        inference = MagicMock()
        inference.return_value = np.array([1.0, 2.0, 3.0])
        result = run_embed(inference, Path("test.wav"))
        assert result.ndim == 1


@pytest.mark.command_graph
class TestEmbedFormatJson:
    def test_valid_json(self):
        emb = np.array([1.0, 2.0, 3.0])
        data = json.loads(embed_format_json(emb, Path("test.wav")))
        assert data["dimension"] == 3
        assert data["embedding"] == [1.0, 2.0, 3.0]
        assert data["file"] == "test.wav"
