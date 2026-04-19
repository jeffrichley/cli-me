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

# Tier-3 real-speech fixtures (downloaded by qa/pyannote/fixtures/fetch_speech_fixtures.py).
# These are intentionally NOT committed — see .gitignore.
SINGLE_SPEAKER = FIXTURES / "single_speaker.wav"
TWO_SPEAKERS = FIXTURES / "two_speakers.wav"

# Skip all tests if no HF token or audio fixture
pytestmark = pytest.mark.integration

has_token = bool(os.environ.get("HF_TOKEN") or Path("E:/cache/huggingface/token").exists())
skip_no_token = pytest.mark.skipif(not has_token, reason="No HF_TOKEN set")
skip_no_audio = pytest.mark.skipif(not TEST_AUDIO.exists(), reason="No test audio fixture")
skip_no_real_speech = pytest.mark.skipif(
    not (SINGLE_SPEAKER.exists() and TWO_SPEAKERS.exists()),
    reason="No real-speech fixtures — run qa/pyannote/fixtures/fetch_speech_fixtures.py",
)


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


# ----------------------------------------------------------------------------
# Tier 3: Real-speech integration tests (the meaningful ones).
#
# The sine-tone fixture above lets us prove the pipeline DOESN'T CRASH on
# arbitrary audio, but speech models return empty results for non-speech, so
# those assertions are necessarily soft. The classes below run on real human
# speech and assert on substantive outputs (segment counts, durations,
# similarity magnitudes). They unlock when the real-speech fixtures exist —
# see qa/pyannote/fixtures/fetch_speech_fixtures.py.
# ----------------------------------------------------------------------------


def _audio_duration(path: Path) -> float:
    """Return audio duration in seconds via the WAV header (no deps)."""
    import struct
    data = path.read_bytes()
    sr = ch = bits = data_bytes = 0
    i = 12
    while i < len(data) - 8:
        cid = data[i:i+4]
        csz = struct.unpack("<I", data[i+4:i+8])[0]
        if cid == b"fmt ":
            _, ch, sr, _, _, bits = struct.unpack("<HHIIHH", data[i+8:i+8+16])
        elif cid == b"data":
            data_bytes = csz
            break
        i += 8 + csz
    return data_bytes / (sr * ch * (bits // 8))


@skip_no_token
@skip_no_real_speech
class TestVadRealSpeech:
    """VAD on real speech — must actually detect speech regions."""

    @pytest.fixture(scope="class")
    def pipeline(self):
        from pyannote_cli.backend import load_pipeline
        return load_pipeline(
            "pyannote/speaker-diarization-community-1",
            device="cpu",
        )

    def test_vad_detects_nonempty_speech(self, pipeline):
        from pyannote_cli.commands.vad import run_vad, format_json
        output = run_vad(pipeline, SINGLE_SPEAKER)
        data = json.loads(format_json(output))
        regions = data["speech_regions"]
        assert len(regions) > 0, "expected at least one speech region on real-speech clip"

    def test_vad_speech_majority_of_clip(self, pipeline):
        from pyannote_cli.commands.vad import run_vad, format_json
        output = run_vad(pipeline, SINGLE_SPEAKER)
        data = json.loads(format_json(output))
        total_speech = sum(r["end"] - r["start"] for r in data["speech_regions"])
        clip_duration = _audio_duration(SINGLE_SPEAKER)
        ratio = total_speech / clip_duration
        assert ratio > 0.5, (
            f"expected >50% of clip to be speech, got {ratio:.2%} "
            f"({total_speech:.2f}s of {clip_duration:.2f}s)"
        )


@skip_no_token
@skip_no_real_speech
class TestDiarizeRealSpeech:
    """Diarization on a clip with two distinct speakers."""

    @pytest.fixture(scope="class")
    def pipeline(self):
        from pyannote_cli.backend import load_pipeline
        return load_pipeline(
            "pyannote/speaker-diarization-community-1",
            device="cpu",
        )

    def test_two_distinct_speakers_detected(self, pipeline):
        from pyannote_cli.commands.diarize import run_diarize
        output = run_diarize(pipeline, TWO_SPEAKERS)
        annotation = output.speaker_diarization if hasattr(output, "speaker_diarization") else output
        labels = annotation.labels()
        assert len(labels) >= 2, (
            f"expected >=2 speaker labels on a 2-speaker clip, got {len(labels)}: {labels}"
        )


def _two_longest_segments_for_distinct_speakers(annotation):
    """Pick one segment per speaker — the longest contiguous segment for each
    of the two most-spoken speakers. Returns (seg_a, label_a, seg_b, label_b)
    or None if fewer than two distinct speakers were detected.
    """
    by_speaker: dict[str, list] = {}
    for segment, _, label in annotation.itertracks(yield_label=True):
        by_speaker.setdefault(label, []).append(segment)
    if len(by_speaker) < 2:
        return None
    # Rank speakers by total speech, then pick longest segment per speaker.
    ranked = sorted(
        by_speaker.items(),
        key=lambda kv: -sum(s.end - s.start for s in kv[1]),
    )
    label_a, segs_a = ranked[0]
    label_b, segs_b = ranked[1]
    seg_a = max(segs_a, key=lambda s: s.end - s.start)
    seg_b = max(segs_b, key=lambda s: s.end - s.start)
    return seg_a, label_a, seg_b, label_b


@skip_no_token
@skip_no_real_speech
class TestEmbedRealSpeech:
    """Speaker embedding similarity on real speech."""

    @pytest.fixture(scope="class")
    def inference(self):
        from pyannote_cli.backend import load_inference
        return load_inference(
            "pyannote/wespeaker-voxceleb-resnet34-LM",
            device="cpu",
            window="whole",
        )

    @pytest.fixture(scope="class")
    def diarization_pipeline(self):
        from pyannote_cli.backend import load_pipeline
        return load_pipeline(
            "pyannote/speaker-diarization-community-1",
            device="cpu",
        )

    def test_same_speaker_high_similarity(self, inference):
        """single_speaker.wav vs itself → similarity > 0.9."""
        from pyannote_cli.commands.verify import cosine_similarity, extract_embedding
        emb1 = extract_embedding(inference, SINGLE_SPEAKER)
        emb2 = extract_embedding(inference, SINGLE_SPEAKER)
        sim = cosine_similarity(emb1, emb2)
        assert sim > 0.9, f"same-file similarity should be > 0.9, got {sim:.4f}"

    def test_different_speakers_lower_similarity(self, inference, diarization_pipeline):
        """Pick segments from two distinct speakers (per diarization) and
        verify their embeddings are meaningfully less similar than two
        embeddings from the same speaker's segment.
        """
        from pyannote.audio import Audio
        from pyannote_cli.commands.diarize import run_diarize
        from pyannote_cli.commands.verify import cosine_similarity
        import numpy as np

        # Diarize to find two distinct speakers.
        d_out = run_diarize(diarization_pipeline, TWO_SPEAKERS)
        ann = d_out.speaker_diarization if hasattr(d_out, "speaker_diarization") else d_out
        picked = _two_longest_segments_for_distinct_speakers(ann)
        assert picked is not None, (
            f"diarization produced fewer than 2 speakers on TWO_SPEAKERS; "
            f"labels={ann.labels()}"
        )
        seg_a, label_a, seg_b, label_b = picked
        assert label_a != label_b

        audio = Audio(sample_rate=16000, mono="downmix")
        wav_a, sr = audio.crop(str(TWO_SPEAKERS), seg_a)
        wav_b, sr2 = audio.crop(str(TWO_SPEAKERS), seg_b)
        assert sr == sr2 == 16000

        def _embed(wav):
            e = inference({"waveform": wav, "sample_rate": sr})
            if isinstance(e, np.ndarray) and e.ndim > 1:
                e = e.squeeze()
            return e

        emb_a1 = _embed(wav_a)
        emb_a2 = _embed(wav_a)  # same-segment baseline
        emb_b = _embed(wav_b)

        self_sim = cosine_similarity(emb_a1, emb_a2)
        cross_sim = cosine_similarity(emb_a1, emb_b)

        # Different speakers should be MEANINGFULLY less similar than the same
        # speaker's segment compared to itself.
        assert cross_sim < self_sim - 0.1, (
            f"different-speaker similarity ({cross_sim:.4f}) should be at least "
            f"0.1 below self-similarity ({self_sim:.4f}); "
            f"speakers compared: {label_a} vs {label_b}"
        )


@skip_no_token
@skip_no_real_speech
class TestVerifyRealSpeech:
    """Speaker verification end-to-end on real speech."""

    @pytest.fixture(scope="class")
    def inference(self):
        from pyannote_cli.backend import load_inference
        return load_inference(
            "pyannote/wespeaker-voxceleb-resnet34-LM",
            device="cpu",
            window="whole",
        )

    @pytest.fixture(scope="class")
    def diarization_pipeline(self):
        from pyannote_cli.backend import load_pipeline
        return load_pipeline(
            "pyannote/speaker-diarization-community-1",
            device="cpu",
        )

    def test_matching_clips_same_speaker_true(self, inference):
        from pyannote_cli.commands.verify import verify_speakers
        result = verify_speakers(inference, SINGLE_SPEAKER, SINGLE_SPEAKER)
        assert result["same_speaker"] is True
        assert result["score"] > 0.9

    def test_mismatched_clips_same_speaker_false(self, inference, diarization_pipeline, tmp_path):
        """Crop two distinct-speaker segments out of two_speakers.wav with
        ffmpeg, then verify them as separate files (verify_speakers' public
        contract takes file paths).
        """
        import subprocess
        from pyannote_cli.commands.diarize import run_diarize
        from pyannote_cli.commands.verify import verify_speakers

        d_out = run_diarize(diarization_pipeline, TWO_SPEAKERS)
        ann = d_out.speaker_diarization if hasattr(d_out, "speaker_diarization") else d_out
        picked = _two_longest_segments_for_distinct_speakers(ann)
        assert picked is not None, (
            f"diarization produced fewer than 2 speakers on TWO_SPEAKERS; "
            f"labels={ann.labels()}"
        )
        seg_a, _, seg_b, _ = picked

        clips = []
        for idx, seg in enumerate((seg_a, seg_b)):
            dest = tmp_path / f"spk_{idx}.wav"
            r = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-ss", f"{seg.start:.3f}", "-t", f"{(seg.end - seg.start):.3f}",
                 "-i", str(TWO_SPEAKERS),
                 "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1", str(dest)],
                capture_output=True, text=True,
            )
            assert r.returncode == 0, f"ffmpeg crop failed: {r.stderr}"
            clips.append(dest)

        result = verify_speakers(inference, clips[0], clips[1])
        # Cross-speaker score should be below the default 0.7 threshold.
        assert result["same_speaker"] is False, (
            f"cross-speaker verification returned same_speaker=True with score {result['score']}"
        )
