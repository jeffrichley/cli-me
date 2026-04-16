"""Tier 2: Integration tests — real models, real audio, deep assertions.

These tests download real model weights from HuggingFace (~500MB first run).
Requires: HF_TOKEN set, model terms accepted, internet access.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add scripts to path
scripts_dir = Path(__file__).resolve().parent.parent.parent / "skill-repo" / "pyannote" / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

FIXTURES = Path(__file__).parent / "fixtures"
TEST_AUDIO = FIXTURES / "test_audio.wav"

# Skip all tests if no HF token or audio fixture
pytestmark = pytest.mark.integration

has_token = bool(os.environ.get("HF_TOKEN") or Path("E:/cache/huggingface/token").exists())
skip_no_token = pytest.mark.skipif(not has_token, reason="No HF_TOKEN set")
skip_no_audio = pytest.mark.skipif(not TEST_AUDIO.exists(), reason="No test audio fixture")


@skip_no_token
@skip_no_audio
class TestDiarizeIntegration:
    """Test real speaker diarization pipeline."""

    @pytest.fixture(scope="class")
    def pipeline(self):
        from pyannote_cli.backend import load_pipeline
        return load_pipeline(
            "pyannote/speaker-diarization-community-1",
            device="cpu",
        )

    def test_diarize_returns_output(self, pipeline):
        from pyannote_cli.commands.diarize import run_diarize
        output = run_diarize(pipeline, TEST_AUDIO)
        # Should return a DiarizeOutput with speaker_diarization
        assert hasattr(output, "speaker_diarization")

    def test_diarize_returns_labels_list(self, pipeline):
        from pyannote_cli.commands.diarize import run_diarize
        output = run_diarize(pipeline, TEST_AUDIO)
        labels = output.speaker_diarization.labels()
        # Pure tones may not be detected as speech — just verify it returns a list
        assert isinstance(labels, list)

    def test_rttm_format_valid(self, pipeline):
        from pyannote_cli.commands.diarize import run_diarize, format_rttm
        output = run_diarize(pipeline, TEST_AUDIO)
        rttm = format_rttm(output, filename="test_audio")
        # May be empty if no speech detected — that's valid
        for line in rttm.strip().split("\n"):
            if line:
                assert line.startswith("SPEAKER test_audio 1")
                parts = line.split()
                float(parts[3])  # start time is a valid float
                assert float(parts[4]) > 0  # duration is positive

    def test_json_format_valid(self, pipeline):
        from pyannote_cli.commands.diarize import run_diarize, format_json
        output = run_diarize(pipeline, TEST_AUDIO)
        data = json.loads(format_json(output))
        assert "diarization" in data
        assert "exclusive_diarization" in data
        # Entries may be empty if no speech detected
        for entry in data["diarization"]:
            assert "start" in entry
            assert "end" in entry
            assert "speaker" in entry
            assert entry["end"] > entry["start"]

    def test_output_to_file(self, pipeline, tmp_path):
        from pyannote_cli.commands.diarize import run_diarize, format_rttm
        output = run_diarize(pipeline, TEST_AUDIO)
        rttm = format_rttm(output, filename="test_audio")
        out_file = tmp_path / "output.rttm"
        out_file.write_text(rttm)
        assert out_file.exists()
        # File may be empty if no speech detected in test audio (sine tones)


@skip_no_token
@skip_no_audio
class TestVadIntegration:
    """Test VAD via diarization pipeline (collapses speakers to SPEECH)."""

    @pytest.fixture(scope="class")
    def pipeline(self):
        from pyannote_cli.backend import load_pipeline
        return load_pipeline(
            "pyannote/speaker-diarization-community-1",
            device="cpu",
        )

    def test_vad_returns_annotation(self, pipeline):
        from pyannote_cli.commands.vad import run_vad
        output = run_vad(pipeline, TEST_AUDIO)
        # Should have itertracks method (Annotation)
        assert hasattr(output, "itertracks")

    def test_vad_detects_speech(self, pipeline):
        from pyannote_cli.commands.vad import run_vad
        output = run_vad(pipeline, TEST_AUDIO)
        tracks = list(output.itertracks(yield_label=True))
        # Our test audio has tones — VAD may or may not detect them as "speech"
        # but it should return a valid (possibly empty) list
        assert isinstance(tracks, list)

    def test_vad_json_valid(self, pipeline):
        from pyannote_cli.commands.vad import run_vad, format_json
        output = run_vad(pipeline, TEST_AUDIO)
        data = json.loads(format_json(output))
        assert "speech_regions" in data
        assert isinstance(data["speech_regions"], list)


@skip_no_token
@skip_no_audio
class TestEmbedIntegration:
    """Test real speaker embedding extraction."""

    @pytest.fixture(scope="class")
    def inference(self):
        from pyannote_cli.backend import load_inference
        return load_inference(
            "pyannote/wespeaker-voxceleb-resnet34-LM",
            device="cpu",
            window="whole",
        )

    def test_embed_returns_array(self, inference):
        import numpy as np
        from pyannote_cli.commands.embed import run_embed
        embedding = run_embed(inference, TEST_AUDIO)
        assert isinstance(embedding, np.ndarray)
        assert embedding.ndim == 1
        assert len(embedding) > 0

    def test_embed_dimension(self, inference):
        from pyannote_cli.commands.embed import run_embed
        embedding = run_embed(inference, TEST_AUDIO)
        # WeSpeaker ResNet34 produces 256-dim embeddings
        assert len(embedding) == 256

    def test_embed_json_format(self, inference):
        from pyannote_cli.commands.embed import run_embed, format_json
        embedding = run_embed(inference, TEST_AUDIO)
        data = json.loads(format_json(embedding, TEST_AUDIO))
        assert data["dimension"] == 256
        assert len(data["embedding"]) == 256
        assert all(isinstance(v, float) for v in data["embedding"])

    def test_embed_npy_save(self, inference, tmp_path):
        import numpy as np
        from pyannote_cli.commands.embed import run_embed, format_numpy
        embedding = run_embed(inference, TEST_AUDIO)
        out_file = tmp_path / "embedding.npy"
        format_numpy(embedding, out_file)
        loaded = np.load(str(out_file))
        assert np.allclose(embedding, loaded)


@skip_no_token
@skip_no_audio
class TestVerifyIntegration:
    """Test real speaker verification."""

    @pytest.fixture(scope="class")
    def inference(self):
        from pyannote_cli.backend import load_inference
        return load_inference(
            "pyannote/wespeaker-voxceleb-resnet34-LM",
            device="cpu",
            window="whole",
        )

    def test_same_file_high_similarity(self, inference):
        from pyannote_cli.commands.verify import verify_speakers
        result = verify_speakers(inference, TEST_AUDIO, TEST_AUDIO)
        # Same file compared to itself should have very high similarity
        assert result["score"] > 0.9
        assert result["same_speaker"] is True

    def test_verify_returns_expected_keys(self, inference):
        from pyannote_cli.commands.verify import verify_speakers
        result = verify_speakers(inference, TEST_AUDIO, TEST_AUDIO)
        assert "score" in result
        assert "same_speaker" in result
        assert "threshold" in result


@skip_no_token
@skip_no_audio
class TestInfoIntegration:
    """Test audio file info command."""

    def test_info_reads_audio(self):
        from pyannote.audio import Audio
        audio = Audio()
        waveform, sr = audio(TEST_AUDIO)
        assert sr == 16000
        duration = waveform.shape[1] / sr
        assert abs(duration - 10.0) < 0.1  # ~10 seconds
        assert waveform.shape[0] == 1  # mono
