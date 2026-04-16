---
title: API Surface
tags: [source-analysis, qwen3-tts]
sources: [https://github.com/QwenLM/Qwen3-TTS]
created: 2026-04-16
updated: 2026-04-16
---

# API Surface

All public methods are on the `Qwen3TTSModel` class in
`qwen_tts/inference/qwen3_tts_model.py`.

## Import

```python
from qwen_tts import Qwen3TTSModel
```

---

## Class: `Qwen3TTSModel`

### `from_pretrained`

```python
@classmethod
def from_pretrained(
    cls,
    pretrained_model_name_or_path: str,
    **kwargs,
) -> "Qwen3TTSModel":
```

Loads the model and its processor in HuggingFace style. `**kwargs` are forwarded
directly to `AutoModel.from_pretrained(...)`.

**Typical kwargs:**
- `device_map` — e.g. `"cuda:0"` or `"auto"`
- `dtype` — e.g. `torch.bfloat16`
- `attn_implementation` — e.g. `"flash_attention_2"`

**Returns:** `Qwen3TTSModel` instance.

---

### `generate_custom_voice`

```python
@torch.no_grad()
def generate_custom_voice(
    self,
    text: Union[str, List[str]],
    speaker: Union[str, List[str]],
    language: Union[str, List[str]] = None,
    instruct: Optional[Union[str, List[str]]] = None,
    non_streaming_mode: bool = True,
    **kwargs,
) -> Tuple[List[np.ndarray], int]:
```

**Model type required:** `custom_voice` (i.e. `Qwen3-TTS-12Hz-*-CustomVoice`)

**Parameters:**
- `text` — text(s) to synthesize; scalar or list
- `speaker` — speaker name(s); validated case-insensitively against `get_supported_speakers()`
- `language` — language name(s); defaults to `"Auto"` if omitted; validated against `get_supported_languages()`
- `instruct` — optional natural-language style instruction(s); `None`/`""` = no instruction; **not supported by 0.6B models** (silently set to `None`)
- `non_streaming_mode` — default `True`; simulates streaming text input when `False`
- `**kwargs` — generation kwargs (see key-functions.md)

**Returns:** `(wavs: List[np.ndarray], sample_rate: int)`

---

### `generate_voice_clone`

```python
@torch.no_grad()
def generate_voice_clone(
    self,
    text: Union[str, List[str]],
    language: Union[str, List[str]] = None,
    ref_audio: Optional[Union[AudioLike, List[AudioLike]]] = None,
    ref_text: Optional[Union[str, List[Optional[str]]]] = None,
    x_vector_only_mode: Union[bool, List[bool]] = False,
    voice_clone_prompt: Optional[Union[Dict[str, Any], List[VoiceClonePromptItem]]] = None,
    non_streaming_mode: bool = False,
    **kwargs,
) -> Tuple[List[np.ndarray], int]:
```

**Model type required:** `base` (i.e. `Qwen3-TTS-12Hz-*-Base`)

**Parameters:**
- `text` — text(s) to synthesize
- `language` — language name(s); defaults to `"Auto"`
- `ref_audio` — reference audio for voice cloning; required if `voice_clone_prompt` is not provided. Accepts: local file path `str`, URL `str`, base64 `str`, `(np.ndarray, sr)` tuple, or list of any of the above
- `ref_text` — transcript of `ref_audio`; required when `x_vector_only_mode=False` (ICL mode)
- `x_vector_only_mode` — if `True`, only speaker embedding is used; `ref_text` not needed but quality may be reduced
- `voice_clone_prompt` — pre-built `List[VoiceClonePromptItem]` from `create_voice_clone_prompt()`, or raw dict; use to avoid recomputing prompt for multiple generations from same speaker
- `non_streaming_mode` — default `False`
- `**kwargs` — generation kwargs (see key-functions.md)

**Returns:** `(wavs: List[np.ndarray], sample_rate: int)`

---

### `generate_voice_design`

```python
@torch.no_grad()
def generate_voice_design(
    self,
    text: Union[str, List[str]],
    instruct: Union[str, List[str]],
    language: Union[str, List[str]] = None,
    non_streaming_mode: bool = True,
    **kwargs,
) -> Tuple[List[np.ndarray], int]:
```

**Model type required:** `voice_design` (i.e. `Qwen3-TTS-12Hz-1.7B-VoiceDesign`)

**Parameters:**
- `text` — text(s) to synthesize
- `instruct` — natural-language description of the desired voice/style; empty string is allowed
- `language` — language name(s); defaults to `"Auto"`
- `non_streaming_mode` — default `True`
- `**kwargs` — generation kwargs (see key-functions.md)

**Returns:** `(wavs: List[np.ndarray], sample_rate: int)`

---

### `create_voice_clone_prompt`

```python
@torch.inference_mode()
def create_voice_clone_prompt(
    self,
    ref_audio: Union[AudioLike, List[AudioLike]],
    ref_text: Optional[Union[str, List[Optional[str]]]] = None,
    x_vector_only_mode: Union[bool, List[bool]] = False,
) -> List[VoiceClonePromptItem]:
```

**Model type required:** `base`

Builds reusable voice-clone prompt items from reference audio. Use this to pre-compute
the speaker features once, then reuse across many `generate_voice_clone()` calls.

**Parameters:**
- `ref_audio` — reference audio(s); same formats as `generate_voice_clone`
- `ref_text` — reference transcript(s); required when `x_vector_only_mode=False`
- `x_vector_only_mode` — if `True`, uses only the x-vector speaker embedding; no ref_text needed

**Returns:** `List[VoiceClonePromptItem]` — each item holds `ref_code`, `ref_spk_embedding`, `x_vector_only_mode`, `icl_mode`, and `ref_text`.

---

### `get_supported_speakers`

```python
def get_supported_speakers(self) -> Optional[List[str]]:
```

Returns a sorted list of supported speaker names (lowercased) for the loaded model,
or `None` if the model does not constrain speakers.

---

### `get_supported_languages`

```python
def get_supported_languages(self) -> Optional[List[str]]:
```

Returns a sorted list of supported language names (lowercased) for the loaded model,
or `None` if the model does not constrain languages.

---

## Type Aliases

```python
AudioLike = Union[
    str,                     # wav path, URL, or base64 string
    np.ndarray,              # not valid alone — must be wrapped in tuple
    Tuple[np.ndarray, int],  # (waveform, sample_rate)
]
```

## Dataclass: `VoiceClonePromptItem`

```python
@dataclass
class VoiceClonePromptItem:
    ref_code: Optional[torch.Tensor]   # (T, Q) or (T,) depending on tokenizer
    ref_spk_embedding: torch.Tensor    # (D,)
    x_vector_only_mode: bool
    icl_mode: bool
    ref_text: Optional[str] = None
```

---

## Supported Speakers (CustomVoice models)

| Speaker    | Native Language         | Voice Description                                    |
|------------|-------------------------|------------------------------------------------------|
| Vivian     | Chinese                 | Bright, slightly edgy young female voice             |
| Serena     | Chinese                 | Warm, gentle young female voice                      |
| Uncle_Fu   | Chinese                 | Seasoned male voice with a low, mellow timbre        |
| Dylan      | Chinese (Beijing)       | Youthful Beijing male voice, clear and natural       |
| Eric       | Chinese (Sichuan)       | Lively Chengdu male voice, slightly husky brightness |
| Ryan       | English                 | Dynamic male voice with strong rhythmic drive        |
| Aiden      | English                 | Sunny American male voice with a clear midrange      |
| Ono_Anna   | Japanese                | Playful Japanese female voice, light and nimble      |
| Sohee      | Korean                  | Warm Korean female voice with rich emotion           |

## Supported Languages (all model variants)

Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian

Language values are case-insensitive. Pass `"Auto"` (or omit `language`) to enable
automatic language detection.
