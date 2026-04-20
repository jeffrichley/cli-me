---
title: State Management
tags: [vnccs, state, filesystem, characters, costumes, emotions]
source: E:/workspaces/tools/comfy/ComfyUI/custom_nodes/ComfyUI_VNCCS/utils.py
date: 2026-04-20
---

# State Management

VNCCS keeps all persistent character state on the ComfyUI filesystem
under a single root directory. There is **no database** — everything is
a directory tree plus one JSON config file per character. This makes the
wrapper's read path straightforward: walk the tree, parse configs. The
wrapper's write path is either (a) submit a workflow that calls the
relevant VNCCS node (which writes state as a side effect) or (b) call
into `utils.py` helpers directly (for operations like "create a costume
entry" where no generation is needed yet).

## Root directory

All state lives under:

```
<ComfyUI-output-dir>/VN_CharacterCreatorSuit/
```

Resolved via `utils.base_output_dir()` (`utils.py:34`):

```python
def base_output_dir() -> str:
    try:
        from folder_paths import get_output_directory
        return os.path.join(get_output_directory(), "VN_CharacterCreatorSuit")
    except ImportError:
        current_dir = os.path.dirname(__file__)
        return os.path.abspath(os.path.join(current_dir, "..", "..", "output", "VN_CharacterCreatorSuit"))
```

On Jeff's install with default ComfyUI layout, that resolves to:

```
E:/workspaces/tools/comfy/ComfyUI/output/VN_CharacterCreatorSuit/
```

If ComfyUI has been launched with `--output-directory`, the VNCCS root
will follow. The wrapper should call ComfyUI's
`folder_paths.get_output_directory()` (via a small Python shim on the
remote ComfyUI instance) or mirror the same "read ComfyUI config"
logic rather than hard-coding the path.

## Per-character tree

Creating a character via `CharacterCreator` calls
`ensure_character_structure(name)` (`utils.py:65`) which materializes:

```
VN_CharacterCreatorSuit/
  {character}/
    {character}_config.json          # Character + costumes metadata
    Sheets/
      Naked/
        neutral/                     # Base unclothed sheet
          sheet_neutral_NNNNN_.png
      {costume_name}/                # One directory per costume
        neutral/
          sheet_neutral_NNNNN_.png
        {emotion_name}/              # One directory per emotion
          sheet_{emotion_name}_NNNNN_.png
    Faces/
      Naked/
        neutral/
          face_neutral_NNNNN_.png
      {costume_name}/
        neutral/
          face_neutral_NNNNN_.png
        {emotion_name}/
          face_{emotion_name}_NNNNN_.png
    Sprites/
      Naked/
        neutral/
          (populated by Stage 4)
      {costume_name}/
        {emotion_name}/
          sprite_{emotion_name}_NNNNN_.png
    lora/                            # Populated by DatasetGenerator
      {costume}_{emotion}_face_{emotion}_NNNNN.png
      {costume}_{emotion}_face_{emotion}_NNNNN.txt
      {costume}_{emotion}_sprite_{emotion}_NNNNN.png
      {costume}_{emotion}_sprite_{emotion}_NNNNN.txt
```

Constants from `utils.py`:

- `EMOTIONS = ["neutral"]` — only `neutral` is created eagerly. Other
  emotions are materialized on demand by `ensure_costume_structure`
  when the user adds them via `EmotionGeneratorV2` or by `EmotionGenerator`
  calling `os.makedirs(face_dir, exist_ok=True)` at runtime.
- `MAIN_DIRS = ["Sprites", "Faces", "Sheets"]` — the three top-level
  subdirectories created for every character.

## `{character}_config.json` schema

Written by `utils.save_config()` (`utils.py:289`). Schema observed from
`CharacterCreator.create_character()` (`character_creator.py:110`):

```json
{
  "character_info": {
    "name": "Alina",
    "background_color": "green",
    "sex": "female",
    "age": 18,
    "race": "human",
    "aesthetics": "masterpiece,best quality,amazing quality",
    "eyes": "blue eyes",
    "hair": "black long",
    "face": "freckles",
    "body": "medium breasts",
    "skin_color": "white",
    "additional_details": "",
    "negative_prompt": "bad quality,worst quality",
    "lora_prompt": "",
    "seed": 1125899906842623,
    "styles_batch": ["optional list from CharacterPreview"],
    "batch_size": 1
  },
  "folder_structure": {
    "main_directories": ["Sprites", "Faces", "Sheets"],
    "emotions": ["neutral"]
  },
  "character_path": "E:/.../output/VN_CharacterCreatorSuit/Alina",
  "config_version": "2.0",
  "costumes": {
    "Naked": {},
    "Casual": {
      "face": "",
      "head": "",
      "top": "white t-shirt",
      "bottom": "blue jeans",
      "shoes": "sneakers",
      "negative_prompt": ""
    }
  }
}
```

Notes on the schema:

- `config_version: "2.0"` — unchanged between VNCCS 2.0 and 2.1.0; the
  wrapper can rely on this.
- `character_info.sex` — newer config format. Older configs used
  `gender`. `utils.load_character_info()` (`utils.py:305`) unifies these
  by setting both keys to the normalized value.
- `costumes` is a dict keyed by costume name. The `"Naked"` entry is
  implicit (hard-coded in `list_costumes`) and does not need to appear in
  the JSON to be returned by `list_costumes()`.
- `seed` of `0` means "pick a new random seed at each generation"
  (`generate_seed()` in `utils.py:127`).

## Naming conventions

### Character name → filesystem

```python
character_path = os.path.join(base_output_dir(), name)          # direct
config_path    = os.path.join(character_path, f"{name}_config.json")
```

`utils.character_dir(name)` (`utils.py:45`) performs the join. There is
**no filename sanitization** in the Python layer. The only sanitization
is in the aiohttp endpoint `/vnccs/create` (`__init__.py:43-48`) which
rejects names containing `/`, `\\`, or `:`. The wrapper should apply the
same safety check before calling into VNCCS.

Character names with spaces, Unicode, or other OS-legal characters work —
they are just directory names. But if the character name contains
characters that ComfyUI's own save-image routines can't handle (e.g.
emoji on some Windows shells), the generation can fail silently.

### Costume name → filesystem

Costumes are subdirectories of `Sheets/`, `Faces/`, and `Sprites/`. They
are created by `ensure_costume_structure(character, costume)`
(`utils.py:96`). The reserved costume name is **`Naked`** (title case) —
hard-coded in `list_costumes()` which always returns it first. Emotion
generation and sprite generation treat `Naked/neutral/` as the base
sheet.

### Emotion name → filesystem

Emotion names come from either (a) the comma-separated `emotions` input
to `EmotionGenerator` (SDXL v1) or (b) the `safe_name` field in
`emotions-config/emotions.json` (Emotion Studio v2). Examples of
`safe_name` values: `angry`, `radiant-smile`, `shy-blush`, `blank-stare`.
Hyphens and dashes are preserved literally as directory names.

### Sheet file naming

Inside each `Sheets/{costume}/{emotion}/` directory, files are named:

```
sheet_{emotion}_NNNNN_.png
```

where `NNNNN` is ComfyUI's auto-incremented sequence number. The
trailing underscore is part of the prefix ComfyUI sees (`sheet_{emotion}_`)
and ComfyUI appends `NNNNN_.png`. `utils.load_character_sheet()`
(`utils.py:392`) walks the directory and picks the file with the highest
number via a regex:

```python
pattern = f"sheet_{emotion}_*(\\d+)_*\\.png"
```

(The escaping is slightly unusual; the effective match is "greatest
integer in the filename".) So repeated generations accumulate and the
most-recent is used. The wrapper can list the files to show the user
history, and can delete older ones to reclaim disk.

Face files follow the same scheme: `face_{emotion}_NNNNN_.png`.
Sprite files: `sprite_{emotion}_NNNNN_.png`.

## Who reads the state

### `list_characters()` (`utils.py:118`)

Returns a sorted list of subdirectory names under `base_output_dir()`.
Silently returns `[]` if the base directory doesn't exist. Used by
`CharacterCreator.INPUT_TYPES`, `CharacterAssetSelector.INPUT_TYPES`,
`EmotionGenerator.INPUT_TYPES`, `EmotionGeneratorV2.INPUT_TYPES`,
`SpriteGenerator.INPUT_TYPES`, `DatasetGenerator.INPUT_TYPES`,
`CharacterPreview` (indirectly).

This is the function the wrapper will call (or replicate) for
`vnccs character list`.

### `list_costumes(character_name)` (`utils.py:485`)

Returns `["Naked", ...]` — always includes `"Naked"` first, then the
costumes declared in the `costumes` dict of the character's config, then
any costume directory names found under `Sheets/` that are not already
in the list (to tolerate manually-added costume directories). The
wrapper calls this for `vnccs clothing list`.

### `load_character_info(character_name)` (`utils.py:305`)

Reads the `{character}_config.json`, returns the `character_info` dict,
and normalizes the `sex`/`gender` key unification. The wrapper uses this
to echo a character's demographics, to build prompts (if the wrapper
wants to replicate the prompt-building logic rather than run the full
workflow), or to let the user inspect the state.

### `load_costume_info(character_name, costume_name)` (`utils.py:372`)

Returns the dict `{face, head, top, bottom, shoes, negative_prompt}` for
a costume, or `{}` if the costume doesn't exist.

### `load_character_sheet(character, costume, emotion, with_mask)` (`utils.py:392`)

Returns the highest-numbered sheet in `Sheets/{costume}/{emotion}/` as a
torch tensor in ComfyUI's `[1, H, W, 4]` RGBA format. Also available
returning `(rgb_tensor, mask_tensor)` when `with_mask=True`. This is
called by `CharacterAssetSelector`, `EmotionGenerator`,
`EmotionGeneratorV2`, and `SpriteGenerator` — the wrapper itself
typically does not call it; it lets the workflow nodes do it.

## Who writes the state

### Full-workflow writes (via ComfyUI `SaveImage`)

All generation output is written by `SaveImage` nodes in the workflow.
The VNCCS nodes produce `*_output_path` strings that look like
`{char_dir}/Sheets/{costume}/{emotion}/sheet_{emotion}_`; ComfyUI's
`SaveImage` reads this prefix and appends `NNNNN_.png`. The writes are
a side effect of running the workflow — the wrapper must submit the
workflow via `POST /prompt` and wait for completion, then discover the
new files by listing the directory (or by parsing ComfyUI's returned
output-file list).

### Config-only writes (no generation)

Some operations change state without rendering anything:

- **Create character** — `CharacterCreator.create_character()` always
  writes `{character}_config.json` even on seed-only changes. The
  HTTP endpoint `/vnccs/create` (`__init__.py:41`) is the documented
  fast path: it calls the same method with defaults and returns the
  config path. The wrapper can use this endpoint for
  `vnccs character create --name X` if a full sheet generation is not
  desired.

- **Create costume** — `/vnccs/create_costume` HTTP endpoint
  (`__init__.py:115`) creates an empty entry in `config["costumes"]` and
  calls `ensure_costume_structure` to materialize the empty directories.
  The wrapper can use this for `vnccs clothing add --name X` when the
  user just wants a slot, or before running the clothing-generation
  workflow.

Both endpoints return JSON with `ok`, `config_path`, and either error
detail or the computed values (prompts, paths, etc.).

## `Sheet Manager` node — what is it really?

`VNCCSSheetManager` is **not** a state-management node despite the name.
It is a **tensor-level** image op that splits a 12-cell sheet into 12
parts or composes 12 parts back into one sheet. It reads no
filesystem state and writes no filesystem state. The filename is
misleading — think of it as "Sheet Split/Compose".

The real state-management nodes are:

- `CharacterCreator` — writes `{character}_config.json` via `save_config`
- `CharacterAssetSelector` / `CharacterAssetSelectorQWEN` — writes
  costume entries via `save_costume_info`
- `EmotionGenerator` / `EmotionGeneratorV2` — calls
  `os.makedirs(face_dir, exist_ok=True)` for each emotion (so the state
  is extended lazily whenever an emotion is produced)
- `DatasetGenerator` — creates `{char_dir}/lora/` and copies files

## `CharacterAssetSelector` — enumeration mechanics

`CharacterAssetSelector.INPUT_TYPES` (`character_selector.py:31-58`)
enumerates every character via `list_characters()` and every costume
across all characters (deduped) for the dropdowns. This is why adding a
new character directory on disk immediately shows up in the ComfyUI UI
the next time a workflow is opened.

The wrapper's `vnccs character list` command should walk the same
directories and display the same state. A lightweight implementation:

```python
import os
root = "<comfy-output-dir>/VN_CharacterCreatorSuit"
for name in sorted(os.listdir(root)):
    config = f"{root}/{name}/{name}_config.json"
    if os.path.exists(config):
        with open(config, 'r', encoding='utf-8') as f:
            data = json.load(f)
        info = data.get("character_info", {})
        print(f"{name}  sex={info.get('sex')} age={info.get('age')} costumes={list(data.get('costumes', {}).keys())}")
```

## `CharacterPreview` — non-writing variant

`CharacterPreview.preview()` (`character_preview.py:63`) does call
`save_config()`, so it **does** persist state. However it does not create
the `Sheets/Faces/Sprites` subdirectories the way `CharacterCreator`
does. Mixed usage can produce a character slot whose config exists but
whose sheet directories don't — the wrapper should tolerate this and
re-run `ensure_character_structure` on any "broken" characters it finds.

## Shared utilities worth importing

These pure-Python helpers (no ComfyUI runtime dependencies beyond
`folder_paths` for `base_output_dir`) can be imported by a
wrapper-side script that runs *inside* the ComfyUI Python environment.
Useful for a `vnccs check` that actually probes the live state rather
than only talking to HTTP.

| Utility | Signature |
|---|---|
| `list_characters()` | `() -> List[str]` |
| `list_costumes(name)` | `(str) -> List[str]` |
| `load_config(name)` | `(str) -> Optional[Dict]` |
| `load_character_info(name)` | `(str) -> Optional[Dict]` |
| `load_costume_info(name, costume)` | `(str, str) -> Dict` |
| `ensure_character_structure(name, emotions, main_dirs)` | creates directories |
| `ensure_costume_structure(name, costume, emotions)` | creates costume directories |
| `save_config(name, data)` | writes the JSON config |
| `save_costume_info(name, costume, data)` | merges into `config["costumes"]` |

## Cross-references

- Node-level triggers for each state change → [`node-surface.md`](node-surface.md)
- Workflow-level outputs (SaveImage prefixes) → [`workflow-stages.md`](workflow-stages.md)
- Models required to produce the sheets → [`required-models.md`](required-models.md)

## Sources

- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\utils.py` (all core state helpers; line 34 for `base_output_dir`, 65 for `ensure_character_structure`, 289 for `save_config`)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\__init__.py` (HTTP endpoints `/vnccs/create`, `/vnccs/create_costume`, `/vnccs/config`)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\character_creator.py` (config write schema, lines 110-142)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\character_selector.py` (enumeration mechanics, lines 31-58, 85-98)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\dataset_generator.py` (lora/ output tree, lines 120-218)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\sheet_manager.py` (note: tensor-only, not state)
- `E:\workspaces\tools\comfy\ComfyUI\custom_nodes\ComfyUI_VNCCS\nodes\sprite_generator.py` (Sprites/ tree walk, lines 44-95)
- README.md usage section (lines 196-244 — confirms tree layout from the user's perspective)
- https://github.com/AHEKOT/ComfyUI_VNCCS/blob/main/utils.py
