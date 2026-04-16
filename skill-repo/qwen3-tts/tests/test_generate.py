"""Tests for generate text command logic."""

from unittest.mock import MagicMock
import numpy as np
import pytest

from qwen3_tts_cli.commands.generate_text import generate_speech


def test_generate_speech_returns_audio_and_sr():
    mock_model = MagicMock()
    mock_model.generate_custom_voice.return_value = ([np.zeros(24000)], 24000)
    audio, sr = generate_speech(
        mock_model,
        text="Hello world",
        language="English",
        speaker="Aiden",
    )
    assert sr == 24000
    assert len(audio) == 24000
    mock_model.generate_custom_voice.assert_called_once_with(
        "Hello world",
        "Aiden",
        language="English",
        instruct=None,
    )


def test_generate_speech_with_instruct():
    mock_model = MagicMock()
    mock_model.generate_custom_voice.return_value = ([np.zeros(24000)], 24000)
    generate_speech(
        mock_model,
        text="I can't believe it!",
        language="English",
        speaker="Aiden",
        instruct="Speak with excitement",
    )
    mock_model.generate_custom_voice.assert_called_once_with(
        "I can't believe it!",
        "Aiden",
        language="English",
        instruct="Speak with excitement",
    )


def test_generate_speech_defaults_language_to_auto():
    mock_model = MagicMock()
    mock_model.generate_custom_voice.return_value = ([np.zeros(24000)], 24000)
    generate_speech(mock_model, text="Hello", speaker="Aiden")
    call_args = mock_model.generate_custom_voice.call_args
    assert call_args[0][1] == "Aiden"  # speaker is second positional arg
    assert call_args[1]["language"] == "Auto"


def test_generate_speech_empty_text_raises():
    mock_model = MagicMock()
    with pytest.raises(ValueError, match="Text must not be empty"):
        generate_speech(mock_model, text="", speaker="Aiden")


def test_generate_speech_empty_speaker_raises():
    mock_model = MagicMock()
    with pytest.raises(ValueError, match="Speaker must not be empty"):
        generate_speech(mock_model, text="Hello", speaker="")
