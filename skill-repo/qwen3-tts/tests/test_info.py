"""Tests for info command logic."""

import json
from unittest.mock import patch, MagicMock

from qwen3_tts_cli.commands.info_device import get_device_info, format_device_info
from qwen3_tts_cli.commands.info_speakers import format_speakers
from qwen3_tts_cli.commands.info_languages import format_languages


def test_get_device_info_cuda():
    with patch("qwen3_tts_cli.commands.info_device.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA RTX 4090"
        mock_props = MagicMock()
        mock_props.total_memory = 24 * 1024**3
        mock_torch.cuda.get_device_properties.return_value = mock_props
        info = get_device_info()
        assert info["device"] == "cuda"
        assert info["gpu_name"] == "NVIDIA RTX 4090"
        assert info["vram_gb"] == 24.0


def test_get_device_info_cpu():
    with patch("qwen3_tts_cli.commands.info_device.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        info = get_device_info()
        assert info["device"] == "cpu"
        assert info["gpu_name"] is None


def test_get_device_info_mps():
    with patch("qwen3_tts_cli.commands.info_device.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True
        info = get_device_info()
        assert info["device"] == "mps"
        assert info["gpu_name"] == "Apple Silicon"


def test_format_device_info_pretty():
    info = {"device": "cuda", "gpu_name": "RTX 4090", "vram_gb": 24.0}
    output = format_device_info(info, pretty=True)
    assert "cuda" in output
    assert "RTX 4090" in output
    assert "24.0" in output


def test_format_device_info_json():
    info = {"device": "cpu", "gpu_name": None, "vram_gb": None}
    output = format_device_info(info, pretty=False)
    parsed = json.loads(output)
    assert parsed["device"] == "cpu"


def test_get_speakers_delegates_to_model():
    from qwen3_tts_cli.commands.info_speakers import get_speakers
    mock_model = MagicMock()
    mock_model.get_supported_speakers.return_value = ["Aiden", "Bella"]
    result = get_speakers(mock_model)
    assert result == ["Aiden", "Bella"]
    mock_model.get_supported_speakers.assert_called_once()


def test_get_speakers_handles_none():
    from qwen3_tts_cli.commands.info_speakers import get_speakers
    mock_model = MagicMock()
    mock_model.get_supported_speakers.return_value = None
    result = get_speakers(mock_model)
    assert result == []


def test_get_languages_delegates_to_model():
    from qwen3_tts_cli.commands.info_languages import get_languages
    mock_model = MagicMock()
    mock_model.get_supported_languages.return_value = ["English", "Chinese"]
    result = get_languages(mock_model)
    assert result == ["English", "Chinese"]
    mock_model.get_supported_languages.assert_called_once()


def test_get_languages_handles_none():
    from qwen3_tts_cli.commands.info_languages import get_languages
    mock_model = MagicMock()
    mock_model.get_supported_languages.return_value = None
    result = get_languages(mock_model)
    assert result == []


def test_format_speakers_pretty():
    speakers = ["Aiden", "Bella", "Carlos"]
    output = format_speakers(speakers, pretty=True)
    assert "Aiden" in output
    assert "Bella" in output
    assert "3" in output  # count


def test_format_speakers_json():
    speakers = ["Aiden", "Bella"]
    output = format_speakers(speakers, pretty=False)
    parsed = json.loads(output)
    assert parsed == ["Aiden", "Bella"]


def test_format_languages_pretty():
    languages = ["English", "Chinese"]
    output = format_languages(languages, pretty=True)
    assert "English" in output
    assert "2" in output  # count


def test_format_languages_json():
    languages = ["English", "Chinese"]
    output = format_languages(languages, pretty=False)
    parsed = json.loads(output)
    assert parsed == ["English", "Chinese"]
