"""Tests for the backend module — device detection, model naming, and audio I/O."""

import pytest
from unittest.mock import patch, MagicMock


def test_detect_device_cuda_available():
    from qwen3_tts_cli.backend import detect_device
    with patch("qwen3_tts_cli.backend.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = True
        assert detect_device() == "cuda"


def test_detect_device_mps_fallback():
    from qwen3_tts_cli.backend import detect_device
    with patch("qwen3_tts_cli.backend.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True
        assert detect_device() == "mps"


def test_detect_device_cpu_fallback():
    from qwen3_tts_cli.backend import detect_device
    with patch("qwen3_tts_cli.backend.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        assert detect_device() == "cpu"


def test_detect_device_force_overrides():
    from qwen3_tts_cli.backend import detect_device
    assert detect_device(force="cpu") == "cpu"
    assert detect_device(force="cuda") == "cuda"


def test_detect_device_force_mps():
    from qwen3_tts_cli.backend import detect_device
    assert detect_device(force="mps") == "mps"


def test_model_name_from_size_1_7b():
    from qwen3_tts_cli.backend import model_name_from_size
    assert model_name_from_size("1.7b") == "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"


def test_model_name_from_size_0_6b():
    from qwen3_tts_cli.backend import model_name_from_size
    assert model_name_from_size("0.6b") == "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"


def test_model_name_invalid_size():
    from qwen3_tts_cli.backend import model_name_from_size
    with pytest.raises(ValueError, match="Unknown model size"):
        model_name_from_size("3b")


def test_base_model_name_from_size():
    from qwen3_tts_cli.backend import base_model_name_from_size
    assert base_model_name_from_size("1.7b") == "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    assert base_model_name_from_size("0.6b") == "Qwen/Qwen3-TTS-12Hz-0.6B-Base"


def test_base_model_name_invalid_size():
    from qwen3_tts_cli.backend import base_model_name_from_size
    with pytest.raises(ValueError, match="Unknown model size"):
        base_model_name_from_size("99b")


def test_design_model_name_from_size():
    from qwen3_tts_cli.backend import design_model_name_from_size
    assert design_model_name_from_size("1.7b") == "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"


def test_design_model_name_invalid_size():
    from qwen3_tts_cli.backend import design_model_name_from_size
    with pytest.raises(ValueError, match="Unknown model size"):
        design_model_name_from_size("0.6b")


def test_save_audio_wav(tmp_path):
    import numpy as np
    from qwen3_tts_cli.backend import save_audio
    audio = np.random.randn(24000).astype(np.float32)
    out = tmp_path / "test.wav"
    result = save_audio(audio, 24000, str(out), format="wav")
    assert result.exists()
    assert result.stat().st_size > 0


def test_save_audio_non_wav_without_ffmpeg(tmp_path):
    import numpy as np
    import click
    from qwen3_tts_cli.backend import save_audio
    audio = np.random.randn(24000).astype(np.float32)
    out = tmp_path / "test.mp3"
    with patch("qwen3_tts_cli.backend.shutil.which", return_value=None):
        with pytest.raises((SystemExit, click.exceptions.Exit)):
            save_audio(audio, 24000, str(out), format="mp3")
