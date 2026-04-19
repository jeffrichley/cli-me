"""Download real-speech fixtures for pyannote tier-3 integration tests.

Why this script exists
----------------------
Sine-tone fixtures don't exercise pyannote — speech-detection models return
empty results, which makes assertion loops vacuous (tests "pass" by asserting
on nothing). To make integration assertions meaningful, we need real human
speech with known structure.

Sources (license-clean)
-----------------------
We pull from two permissively-licensed upstreams:

  - SpeechBrain test ASR samples (Apache 2.0,
    https://github.com/speechbrain/speechbrain) — `spk1_snt1.wav`, used to
    build a single-speaker fixture by concatenating three copies with brief
    silences.
  - pyannote-audio tutorial sample (MIT,
    https://github.com/pyannote/pyannote-audio) — `sample.wav`, a 30s
    multi-speaker conversational clip used unchanged as `two_speakers.wav`.
    This is pyannote's own canonical diarization demo audio and reliably
    produces >=2 distinct speaker labels.

Outputs
-------
  - single_speaker.wav  ~9.0s   spk1 + 0.2s sil + spk1 + 0.2s sil + spk1
  - two_speakers.wav    ~30.0s  pyannote tutorial sample.wav (verbatim copy)

Hashes for every upstream file are baked in so we never trust the network
blindly. The single-speaker fixture is deterministic byte-for-byte
(ffmpeg PCM concat of identical inputs) so its post-build hash is verified
too.

Usage
-----
    python qa/pyannote/fixtures/fetch_speech_fixtures.py

Idempotent: skips work if output files already exist with correct hashes.
Requires: Python stdlib + ffmpeg on PATH. No pip dependencies.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent

# Upstream sources — SpeechBrain test assets (Apache 2.0) + pyannote tutorial (MIT).
SOURCES = {
    "spk1_snt1.wav": {
        "url": "https://github.com/speechbrain/speechbrain/raw/develop/tests/samples/ASR/spk1_snt1.wav",
        "sha256": "2f7315ccf543b6368528b098cd895098c154f222cd55ff7b5f66b50feb383c56",
        "size": 91884,
    },
    "pyannote_sample.wav": {
        "url": "https://github.com/pyannote/pyannote-audio/raw/develop/tutorials/assets/sample.wav",
        "sha256": "c319b4abca767b124e41432d364fd7df006cb26bb79d09326c487d606a134e6e",
        "size": 960104,
    },
}

# Final fixtures.
#  - single_speaker.wav: ffmpeg concat of three spk1_snt1.wav copies w/ silence — deterministic.
#  - two_speakers.wav:   verbatim copy of pyannote_sample.wav — same hash as upstream.
FIXTURES = {
    "single_speaker.wav": "b559c6befeee70f27051c4620653377b1ec46e9e0ec467962ec92ffff10d6e7d",
    "two_speakers.wav": "c319b4abca767b124e41432d364fd7df006cb26bb79d09326c487d606a134e6e",
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "cli-me-fixture-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)


def fetch_source(name: str, spec: dict, work_dir: Path) -> Path:
    out = work_dir / name
    print(f"source: {name}")
    download(spec["url"], out)
    actual = sha256_of(out)
    if actual != spec["sha256"]:
        raise RuntimeError(
            f"hash mismatch for {name}\n"
            f"  expected: {spec['sha256']}\n"
            f"  actual:   {actual}\n"
            f"Refusing to use untrusted bytes."
        )
    print(f"  hash OK ({spec['size']} bytes)")
    return out


def ffmpeg(*args: str) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n  cmd: {' '.join(cmd)}\n  stderr: {result.stderr}")


def make_silence(duration: float, dest: Path) -> None:
    ffmpeg(
        "-f", "lavfi",
        "-i", f"anullsrc=channel_layout=mono:sample_rate=16000",
        "-t", f"{duration}",
        "-c:a", "pcm_s16le",
        str(dest),
    )


def concat_pcm(parts: list[Path], dest: Path, work_dir: Path) -> None:
    """Concatenate WAV files via ffmpeg's concat demuxer with PCM re-encoding.

    Re-encoding to pcm_s16le 16kHz mono guarantees a deterministic header and
    exact byte-for-byte reproducibility across machines.
    """
    list_file = work_dir / f"{dest.stem}_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{p.as_posix()}'\n")
    ffmpeg(
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c:a", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(dest),
    )


def all_fixtures_present() -> bool:
    for name, expected in FIXTURES.items():
        path = FIXTURES_DIR / name
        if not path.exists():
            return False
        if sha256_of(path) != expected:
            return False
    return True


def build() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    if all_fixtures_present():
        print("all fixtures already present with correct hashes — nothing to do")
        for name in FIXTURES:
            print(f"  ok  {FIXTURES_DIR / name}")
        return

    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found on PATH. Install ffmpeg to build fixtures.", file=sys.stderr)
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="pyannote_fixprep_") as tmp:
        work = Path(tmp)

        # 1. fetch upstream sources with hash verification
        spk1 = fetch_source("spk1_snt1.wav", SOURCES["spk1_snt1.wav"], work)
        pyannote_sample = fetch_source(
            "pyannote_sample.wav", SOURCES["pyannote_sample.wav"], work
        )

        # 2. build silences for the single-speaker concat
        sil_short = work / "sil_short.wav"
        print("building silence (0.2s) at 16kHz mono PCM")
        make_silence(0.2, sil_short)

        # 3. assemble single_speaker.wav  (spk1 x3 with short silences)
        single_dest = FIXTURES_DIR / "single_speaker.wav"
        print(f"assembling {single_dest.name}")
        concat_pcm([spk1, sil_short, spk1, sil_short, spk1], single_dest, work)

        # 4. two_speakers.wav is the pyannote tutorial sample, verbatim.
        two_dest = FIXTURES_DIR / "two_speakers.wav"
        print(f"installing {two_dest.name} (verbatim copy of pyannote tutorial sample)")
        shutil.copyfile(pyannote_sample, two_dest)

    # 5. verify final hashes
    print("verifying final fixture hashes")
    failures = []
    for name, expected in FIXTURES.items():
        path = FIXTURES_DIR / name
        actual = sha256_of(path)
        size = path.stat().st_size
        if actual == expected:
            print(f"  ok  {name}  ({size} bytes, sha256={actual[:16]}...)")
        else:
            print(f"  FAIL {name}\n    expected: {expected}\n    actual:   {actual}")
            failures.append(name)

    if failures:
        print(
            "\nfixture hash verification failed. This usually means ffmpeg produced\n"
            "different output than expected (different version or codec build).\n"
            "Inspect the files manually before using.",
            file=sys.stderr,
        )
        sys.exit(2)

    print("done")


if __name__ == "__main__":
    build()
