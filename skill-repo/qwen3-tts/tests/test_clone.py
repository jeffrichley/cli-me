"""Tests for clone text command logic."""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from qwen3_tts_cli.commands.clone_text import clone_speech


def test_clone_speech_calls_generate_voice_clone(tmp_path):
    ref_file = tmp_path / "voice.wav"
    ref_file.touch()
    mock_model = MagicMock()
    mock_model.generate_voice_clone.return_value = ([np.zeros(24000)], 24000)
    audio, sr = clone_speech(
        mock_model,
        text="Hello",
        language="English",
        reference=str(ref_file),
        ref_text="This is the reference transcript.",
    )
    assert sr == 24000
    assert len(audio) == 24000
    call_kwargs = mock_model.generate_voice_clone.call_args[1]
    assert call_kwargs["ref_audio"] == str(ref_file)
    assert call_kwargs["ref_text"] == "This is the reference transcript."


def test_clone_speech_defaults_language_to_auto(tmp_path):
    ref_file = tmp_path / "voice.wav"
    ref_file.touch()
    mock_model = MagicMock()
    mock_model.generate_voice_clone.return_value = ([np.zeros(24000)], 24000)
    clone_speech(mock_model, text="Hello", reference=str(ref_file), ref_text="text")
    call_kwargs = mock_model.generate_voice_clone.call_args[1]
    assert call_kwargs["language"] == "Auto"


def test_clone_speech_validates_reference_exists():
    mock_model = MagicMock()
    with pytest.raises(FileNotFoundError, match="Reference audio file not found"):
        clone_speech(
            mock_model,
            text="Hello",
            reference="/nonexistent/file.wav",
            ref_text="text",
        )


def test_clone_speech_validates_empty_text(tmp_path):
    ref_file = tmp_path / "voice.wav"
    ref_file.touch()
    mock_model = MagicMock()
    with pytest.raises(ValueError, match="Text must not be empty"):
        clone_speech(mock_model, text="", reference=str(ref_file), ref_text="text")


def test_clone_speech_validates_empty_ref_text(tmp_path):
    ref_file = tmp_path / "voice.wav"
    ref_file.touch()
    mock_model = MagicMock()
    with pytest.raises(ValueError, match="Reference text must not be empty"):
        clone_speech(mock_model, text="Hello", reference=str(ref_file), ref_text="")
