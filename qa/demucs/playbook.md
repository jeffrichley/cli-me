# Demucs QA Playbook

## Command: `separate`

### What it does
Splits an audio file into individual stems (vocals, drums, bass, other)
using Demucs's neural network models.

### Inputs & Expected Outputs

| Input | Flags | Expected Output |
|-------|-------|-----------------|
| `song.mp3` | (none) | 4 WAV files in `separated/htdemucs/song/`: vocals.wav, drums.wav, bass.wav, other.wav |
| `song.mp3` | `--two-stems vocals` | 2 files: vocals.wav, no_vocals.wav |
| `song.mp3` | `--model htdemucs_ft` | Same 4 stems, using fine-tuned model |
| `song.mp3` | `--format mp3` | 4 MP3 files instead of WAV |
| `song.mp3` | `--format flac` | 4 FLAC files instead of WAV |
| `song.mp3` | `--device cpu` | Same output, forced CPU processing |
| `song.mp3` | `--device cuda` | Same output, forced GPU processing |
| `song.mp3` | `--shifts 5` | Same output, higher quality |
| `song.mp3` | `--segment 8` | Same output, lower VRAM usage |
| `song.mp3` | `--output ./my-stems` | Stems in `my-stems/htdemucs/song/` |
| `a.mp3 b.mp3` | (none) | Stems for both files in separate dirs |

### Verification Methods

**Tier 1 (command_graph)**: Call `build_args()` directly (pure function, no mocks).
Assert the correct demucs argument list is built for each flag combination,
including file position at the end of the args list.

**Tier 2 (integration)**: Generate a 3-second synthetic audio file with
ffmpeg. Run real demucs separation. Verify:
- All expected stem files exist and are nonzero
- Audio properties: correct sample rate (44100), correct channels (2), correct codec
- Duration approximately matches input duration
- Two-stems mode produces exactly 2 files
- MP3 output has correct codec

**Tier 3 (manual)**: Separate a real song, listen to each stem for
quality. Check that vocals are clean, drums are isolated, etc.

### Edge Cases
- Empty audio file (0 duration)
- Very short audio (<1 second)
- Non-audio file (image, text)
- File with spaces in name
- Non-ASCII characters in path
- Invalid model name
- Invalid device string
- `--segment` set too small

## Command: `list-models`

### What it does
Lists all available pretrained Demucs models.

### Inputs & Expected Outputs
| Input | Expected Output |
|-------|-----------------|
| (none) | Table or list of model names with descriptions |

### Verification Methods
**Tier 1**: Test `MODEL_DESCRIPTIONS` dict and `build_output()` formatting
(mocks `find_model_configs()` for deterministic output).
**Tier 2**: Run real command. Assert output contains known model names (htdemucs, mdx).
