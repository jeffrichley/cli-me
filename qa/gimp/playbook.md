# gimp Skill - QA Playbook

Command groups in scope:
- `info` (`version`, `capabilities`)
- `batch` (`run`)
- `pod` (`resize`, `fit-crop`, `prep`)

## info group

### `info version`
- Signature: `gimp-cli info version`
- Behavior: runs GIMP with `--version` and prints raw version line
- Verification:
  - Tier 1: args are exactly `["--version"]`
  - Tier 2: output contains `GIMP` or version token
- Error contract:
  - missing binary -> exit 1 with install instructions

### `info capabilities`
- Signature: `gimp-cli info capabilities`
- Behavior: prints resolved binary path and wrapper-supported flags
- Verification:
  - Tier 1: includes expected flags list
  - Tier 2: when binary present, prints non-empty path

## batch group

### `batch run`
- Signature:
  - `gimp-cli batch run --command <expr> [--command <expr> ...] [--interpreter <proc>] [--no-data] [--no-fonts] [--verbose] [--keep-alive]`
- Behavior:
  - constructs deterministic non-interactive argv
  - default flags: `--new-instance --no-interface --console-messages --no-splash`
  - emits repeated `--batch <expr>` for each command
  - appends `--quit` unless `--keep-alive`
- Verification:
  - Tier 1: exact argv comparison including kitchen-sink all-options case
  - Tier 2: runs a minimal quit expression and exits 0 when GIMP is available
- Error contract:
  - if GIMP returns non-zero, command exits with same code and forwards stderr

## Edge cases to cover

- repeated `--command` ordering
- interpreter optional vs provided
- keep-alive removes `--quit`
- paths/strings with spaces in expressions preserved as single args

## pod group

### `pod resize`
- Signature:
  - `gimp-cli pod resize --input <path> --output <path> --width <px> --height <px> [--interpolation none|linear|cubic|lanczos] [--flatten]`
- Behavior:
  - builds Scheme expression that loads file, scales, optional flatten, saves output
- Verification:
  - Tier 1: expression contains load/scale/save contract + selected dimensions
  - Tier 2: output image dimensions match requested width/height

### `pod fit-crop`
- Signature:
  - `gimp-cli pod fit-crop --input <path> --output <path> --width <px> --height <px> [--anchor center|top|bottom|left|right] [--flatten]`
- Behavior:
  - scale-to-fill then crop to exact target dimensions
- Verification:
  - Tier 1: expression includes crop call with target dimensions and crop offsets
  - Tier 2: output image dimensions match requested width/height

### `pod prep`
- Signature:
  - `gimp-cli pod prep --input <path> --output <path> --width <px> --height <px> [--dpi <int>] [--flatten]`
- Behavior:
  - one-shot prep for print: scale, set resolution metadata, optional flatten, save
- Verification:
  - Tier 1: expression includes scale + set-resolution + save
  - Tier 2: output size matches and command exits cleanly on real GIMP
