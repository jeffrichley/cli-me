"""Tier 2: Integration tests for Demucs CLI.

These tests run the real demucs binary against synthetic audio fixtures.
Skips if demucs is not installed.

NOTE: On Windows with torchaudio >= 2.11 and the "essentials" ffmpeg build,
WAV/FLAC saving may fail due to torchcodec requiring ffmpeg shared DLLs.
MP3 output uses lameenc (pure Python) and always works. Tests that require
WAV/FLAC output are marked to xfail on this known environment issue.
"""

import sys
import subprocess
import pytest
from pathlib import Path

# Add the scripts directory to the path
sys.path.insert(
    0,
    str(
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "skill-repo"
        / "demucs"
        / "scripts"
    ),
)

from demucs_cli.commands import separate_audio, list_models
from demucs_cli.backend import find_executable

# Also add qa/ to path for conftest helpers
sys.path.insert(
    0,
    str(__import__("pathlib").Path(__file__).resolve().parents[1]),
)

STEMS_4 = {"vocals", "drums", "bass", "other"}


def run_demucs(args: list[str], timeout: int = 300, exe: str | None = None) -> subprocess.CompletedProcess:
    """Run demucs with the given args using the provided executable path."""
    if exe is None:
        exe = find_executable()
    return subprocess.run(
        [exe] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )



# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def short_audio(tmp_path, ffmpeg_path):
    """Generate a 5-second stereo test audio file with multiple frequencies."""
    output = tmp_path / "test_song.wav"
    subprocess.run(
        [
            ffmpeg_path, "-y",
            "-f", "lavfi", "-i",
            "sine=frequency=440:duration=5",
            "-f", "lavfi", "-i",
            "sine=frequency=220:duration=5",
            "-filter_complex",
            "[0:a][1:a]amerge=inputs=2,pan=stereo|c0=c0|c1=c1[aout]",
            "-map", "[aout]",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    return output


# ─── separate command ───────────────────────────────────────────────��────────


@pytest.mark.integration
class TestSeparateIntegration:

    def test_mp3_separation_produces_4_stems(
        self, demucs_path, short_audio, tmp_path, ffprobe_path
    ):
        """MP3 separation produces 4 MP3 stem files with correct properties."""
        output_dir = tmp_path / "output"
        args = separate_audio.build_args(
            [str(short_audio)],
            output=str(output_dir),
            device="cpu",
            shifts=0,
            format="mp3",
        )
        result = run_demucs(args, timeout=300, exe=demucs_path)
        assert result.returncode == 0, f"demucs failed: {result.stderr}"

        # Find output files — structure is {output}/htdemucs/{track_name}/
        model_dir = output_dir / "htdemucs"
        assert model_dir.exists(), f"Model output dir missing: {model_dir}"

        track_dirs = list(model_dir.iterdir())
        assert len(track_dirs) == 1, f"Expected 1 track dir, got {len(track_dirs)}"

        track_dir = track_dirs[0]
        mp3_files = {f.stem: f for f in track_dir.glob("*.mp3")}
        assert set(mp3_files.keys()) == STEMS_4, (
            f"Expected stems {STEMS_4}, got {set(mp3_files.keys())}"
        )

        # Verify each stem has correct audio properties
        for stem_name, stem_path in mp3_files.items():
            assert stem_path.stat().st_size > 0, f"{stem_name} is empty"

            from conftest import probe_format
            data = probe_format(ffprobe_path, stem_path)
            audio_streams = [
                s for s in data.get("streams", [])
                if s.get("codec_type") == "audio"
            ]
            assert len(audio_streams) == 1, f"{stem_name}: no audio stream"
            stream = audio_streams[0]

            assert stream["codec_name"] == "mp3", (
                f"{stem_name}: expected mp3 codec, got {stream['codec_name']}"
            )
            assert stream["sample_rate"] == "44100", (
                f"{stem_name}: expected 44100 Hz, got {stream['sample_rate']}"
            )
            assert int(stream["channels"]) == 2, (
                f"{stem_name}: expected 2 channels, got {stream['channels']}"
            )

        # Verify duration approximately matches input (5 seconds)
        from conftest import assert_duration_approx
        first_stem = next(iter(mp3_files.values()))
        assert_duration_approx(ffprobe_path, first_stem, 5.0, tolerance=1.0)

    def test_two_stems_vocals_mp3(
        self, demucs_path, short_audio, tmp_path
    ):
        """Two-stem mode produces exactly 2 MP3 files: vocals + no_vocals."""
        output_dir = tmp_path / "output"
        args = separate_audio.build_args(
            [str(short_audio)],
            output=str(output_dir),
            device="cpu",
            shifts=0,
            two_stems="vocals",
            format="mp3",
        )
        result = run_demucs(args, timeout=300, exe=demucs_path)
        assert result.returncode == 0, f"demucs failed: {result.stderr}"

        model_dir = output_dir / "htdemucs"
        track_dirs = list(model_dir.iterdir())
        track_dir = track_dirs[0]

        mp3_files = list(track_dir.glob("*.mp3"))
        stem_names = {f.stem for f in mp3_files}
        assert "vocals" in stem_names, f"vocals.mp3 missing, got {stem_names}"
        assert "no_vocals" in stem_names, f"no_vocals.mp3 missing, got {stem_names}"
        assert len(mp3_files) == 2, f"Expected 2 files, got {len(mp3_files)}"

    def test_wav_separation(
        self, demucs_path, short_audio, tmp_path, ffprobe_path
    ):
        """WAV separation produces 4 WAV stem files with correct properties.

        Requires ffmpeg full-shared build on Windows for torchaudio >= 2.11.
        """
        output_dir = tmp_path / "output"
        args = separate_audio.build_args(
            [str(short_audio)],
            output=str(output_dir),
            device="cpu",
            shifts=0,
        )
        result = run_demucs(args, timeout=300, exe=demucs_path)
        assert result.returncode == 0, f"demucs failed: {result.stderr}"

        model_dir = output_dir / "htdemucs"
        track_dirs = list(model_dir.iterdir())
        track_dir = track_dirs[0]

        wav_files = {f.stem: f for f in track_dir.glob("*.wav")}
        assert set(wav_files.keys()) == STEMS_4

        for stem_name, stem_path in wav_files.items():
            assert stem_path.stat().st_size > 0, f"{stem_name} is empty"
            from conftest import probe_format
            data = probe_format(ffprobe_path, stem_path)
            audio = [s for s in data["streams"] if s["codec_type"] == "audio"]
            assert len(audio) == 1, f"{stem_name}: no audio stream"
            assert audio[0]["sample_rate"] == "44100"
            assert int(audio[0]["channels"]) == 2

    def test_flac_separation(
        self, demucs_path, short_audio, tmp_path, ffprobe_path
    ):
        """FLAC separation produces 4 FLAC stem files with correct properties.

        Requires ffmpeg full-shared build on Windows for torchaudio >= 2.11.
        """
        output_dir = tmp_path / "output"
        args = separate_audio.build_args(
            [str(short_audio)],
            output=str(output_dir),
            device="cpu",
            shifts=0,
            format="flac",
        )
        result = run_demucs(args, timeout=300)
        assert result.returncode == 0, f"demucs failed: {result.stderr}"

        model_dir = output_dir / "htdemucs"
        track_dirs = list(model_dir.iterdir())
        track_dir = track_dirs[0]

        flac_files = {f.stem: f for f in track_dir.glob("*.flac")}
        assert set(flac_files.keys()) == STEMS_4

        for stem_name, stem_path in flac_files.items():
            assert stem_path.stat().st_size > 0, f"{stem_name} is empty"
            from conftest import probe_format
            data = probe_format(ffprobe_path, stem_path)
            audio = [s for s in data["streams"] if s["codec_type"] == "audio"]
            assert len(audio) == 1, f"{stem_name}: no audio stream"
            assert audio[0]["codec_name"] == "flac"
            assert audio[0]["sample_rate"] == "44100"


# ─── list-models command ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestListModelsIntegration:

    def test_list_models_shows_known_models(self, demucs_path):
        """list-models finds known model configs."""
        models = list_models.find_model_configs()
        assert len(models) > 0, "No models found"
        assert "htdemucs" in models, f"htdemucs not in {models}"
        assert "mdx" in models, f"mdx not in {models}"

        # Also test the formatted output
        output = list_models.build_output()
        assert "htdemucs" in output
        assert "Available Demucs models" in output
