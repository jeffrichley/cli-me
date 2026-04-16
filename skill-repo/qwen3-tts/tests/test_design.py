"""Tests for design text command logic."""

from unittest.mock import MagicMock
import numpy as np
import pytest

from qwen3_tts_cli.commands.design_text import design_speech


def test_design_speech_calls_generate_voice_design():
    mock_model = MagicMock()
    mock_model.generate_voice_design.return_value = ([np.zeros(24000)], 24000)
    audio, sr = design_speech(
        mock_model,
        text="Good morning",
        language="English",
        description="A warm, deep male voice with a calm tone",
    )
    assert sr == 24000
    assert len(audio) == 24000
    mock_model.generate_voice_design.assert_called_once_with(
        "Good morning",
        "A warm, deep male voice with a calm tone",
        language="English",
    )


def test_design_speech_defaults_language_to_auto():
    mock_model = MagicMock()
    mock_model.generate_voice_design.return_value = ([np.zeros(24000)], 24000)
    design_speech(mock_model, text="Hi", description="warm voice")
    call_args = mock_model.generate_voice_design.call_args
    assert call_args[0][1] == "warm voice"  # description is second positional arg
    assert call_args[1]["language"] == "Auto"


def test_design_speech_validates_empty_description():
    mock_model = MagicMock()
    with pytest.raises(ValueError, match="description"):
        design_speech(mock_model, text="Hi", description="")


def test_design_speech_validates_empty_text():
    mock_model = MagicMock()
    with pytest.raises(ValueError, match="Text must not be empty"):
        design_speech(mock_model, text="", description="warm voice")
