"""Tests for finetune command logic."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np

from qwen3_tts_cli.commands.finetune_prepare import validate_audio_dir
from qwen3_tts_cli.commands.finetune_train import build_train_args
from qwen3_tts_cli.commands.finetune_generate import generate_from_finetuned


def test_validate_audio_dir_with_wav_files(tmp_path):
    (tmp_path / "sample1.wav").write_bytes(b"RIFF" + b"\x00" * 100)
    (tmp_path / "sample2.wav").write_bytes(b"RIFF" + b"\x00" * 100)
    result = validate_audio_dir(str(tmp_path))
    assert result["wav_count"] == 2
    assert result["valid"] is True


def test_validate_audio_dir_empty(tmp_path):
    result = validate_audio_dir(str(tmp_path))
    assert result["wav_count"] == 0
    assert result["valid"] is False


def test_validate_audio_dir_nonexistent():
    with pytest.raises(FileNotFoundError):
        validate_audio_dir("/nonexistent/dir")


def test_validate_audio_dir_ignores_non_wav(tmp_path):
    (tmp_path / "readme.txt").write_text("not audio")
    (tmp_path / "sample.wav").write_bytes(b"RIFF" + b"\x00" * 100)
    result = validate_audio_dir(str(tmp_path))
    assert result["wav_count"] == 1


def test_build_train_args_defaults():
    args = build_train_args(
        dataset="/data/train.jsonl",
        output_dir="/output/model",
        base_model="1.7b",
    )
    assert "--init_model_path" in args
    assert "Qwen/Qwen3-TTS-12Hz-1.7B-Base" in args
    assert "--output_model_path" in args
    assert "/output/model" in args
    assert "--train_jsonl" in args
    assert "/data/train.jsonl" in args


def test_build_train_args_custom_params():
    args = build_train_args(
        dataset="/data/train.jsonl",
        output_dir="/output",
        base_model="0.6b",
        epochs=20,
        batch_size=16,
        learning_rate=1e-5,
    )
    idx = args.index("--num_epochs")
    assert args[idx + 1] == "20"
    idx = args.index("--batch_size")
    assert args[idx + 1] == "16"
    idx = args.index("--lr")
    assert args[idx + 1] == "1e-05"
    assert "Qwen/Qwen3-TTS-12Hz-0.6B-Base" in args


def test_build_train_args_invalid_base_model():
    with pytest.raises(ValueError, match="Unknown model size"):
        build_train_args(dataset="x", output_dir="y", base_model="99b")


def test_generate_from_finetuned_returns_audio():
    mock_model = MagicMock()
    mock_model.generate_custom_voice.return_value = ([np.zeros(24000)], 24000)
    audio, sr = generate_from_finetuned(
        model=mock_model,
        text="Hello",
        language="English",
    )
    assert sr == 24000
    assert len(audio) == 24000
    # Verify correct arg order: (text, speaker, language=..., instruct=...)
    mock_model.generate_custom_voice.assert_called_once_with(
        "Hello",
        "custom_speaker",
        language="English",
        instruct=None,
    )


def test_generate_from_finetuned_with_instruct():
    mock_model = MagicMock()
    mock_model.generate_custom_voice.return_value = ([np.zeros(24000)], 24000)
    generate_from_finetuned(
        model=mock_model,
        text="Hello",
        instruct="Speak softly",
    )
    mock_model.generate_custom_voice.assert_called_once_with(
        "Hello",
        "custom_speaker",
        language="Auto",
        instruct="Speak softly",
    )


def test_build_train_args_model_follows_flag():
    args = build_train_args(dataset="/data/t.jsonl", output_dir="/out", base_model="1.7b")
    idx = args.index("--init_model_path")
    assert args[idx + 1] == "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def test_build_train_args_speaker_name_default():
    args = build_train_args(dataset="/data/t.jsonl", output_dir="/out")
    idx = args.index("--speaker_name")
    assert args[idx + 1] == "custom_speaker"


def test_build_train_args_custom_speaker():
    args = build_train_args(dataset="/data/t.jsonl", output_dir="/out", speaker_name="jeff")
    idx = args.index("--speaker_name")
    assert args[idx + 1] == "jeff"


def test_generate_from_finetuned_empty_text():
    mock_model = MagicMock()
    with pytest.raises(ValueError, match="Text must not be empty"):
        generate_from_finetuned(model=mock_model, text="")
