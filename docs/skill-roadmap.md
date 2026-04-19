# Skill Roadmap

Planned skills for cli-me, in priority order.

## Done

| Skill | Software | Backend Pattern | Status |
|-------|----------|----------------|--------|
| ffmpeg | ffmpeg | subprocess | Shipped. 35 wiki pages, 34 CLI commands, 168 tests, 3 adversarial review rounds |

## Up Next — TTS / Voice Pipeline

| Skill | Software | Backend Pattern | Why |
|-------|----------|----------------|-----|
| yt-dlp | yt-dlp | subprocess | Download video/audio from YouTube + 80 sites. Simplest next skill, validates new process 🌶️🌶️ |
| demucs | Demucs (Meta) | Python (demucs library) | Separate vocals from music/noise. GPU-accelerated on 4060 Ti 🌶️ |
| qwen3-tts | Qwen3-TTS + transformers | Python (torch) | TTS: voice cloning, voice engineering, streaming, batch generation 🌶️🌶️🌶️🌶️🌶️ |
| pyannote | pyannote-audio | Python (pyannote library) | Speaker diarization — isolate individual speakers from multi-speaker audio 🌶️ |

## Up Next — Viral / Community

| Skill | Software | Backend Pattern | Why |
|-------|----------|----------------|-----|
| obs-studio | OBS Studio | obs-websocket (REST) | Huge streamer audience, vocal community |
| davinci-resolve | DaVinci Resolve | scripting API (Lua/Python) | Free video editor, massive YouTuber base |

## Core Pipeline (Jeff's creative toolchain)

| Skill | Software | Backend Pattern | Why |
|-------|----------|----------------|-----|
| gimp | GIMP | subprocess (Python-Fu headless) | Image editing, POD graphic cleanup 🌶️🌶️🌶️ |
| blender | Blender | subprocess (`blender --background --python`) | 3D modeling, rendering 🌶️ |
| comfyui | ComfyUI | REST API (localhost:8188) | AI image generation 🌶️🌶️🌶️🌶️ |
| comfyui-vnccs | ComfyUI_VNCCS | REST API via ComfyUI (custom nodes) | Consistent character sprites 🌶️🌶️🌶️ |
| kohya-ss | kohya_ss | subprocess (training scripts) | LoRA model training (image) 🌶️🌶️ |

## Wishlist

Add ideas here. Move to "Up Next" when ready to build.

| Skill | Software | Backend Pattern | Notes |
|-------|----------|----------------|-------|
| inkscape | Inkscape | subprocess (`inkscape --actions`) | SVG editing, POD vector work 🌶️ |
| imagemagick | ImageMagick | subprocess | Batch image processing, complements ffmpeg 🌶️🌶️🌶️ |
| krita | Krita | scripting API | Digital painting, art community |
| audacity | Audacity | subprocess (sox) | Audio editing, podcasters |
| godot | Godot | subprocess (headless) | Game engine, indie dev community |
| pandoc | Pandoc | subprocess | Document format conversion (md→PDF, HTML→md). Render 47 Tabs pitches, PhD drafts, NIWC docs 🌶️🌶️🌶️🌶️ |
| rsvg-convert | librsvg | subprocess | SVG→PNG rendering for Discord embeds, visual briefs, project cards 🌶️🌶️ |
| tesseract | Tesseract OCR | subprocess | Extract text from images/screenshots. Read what Jeff pastes, process scanned docs 🌶️🌶️ |
