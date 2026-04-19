# Skill Roadmap

Planned skills for cli-me, in priority order.

## Done

| Skill | Software | Backend Pattern | Status |
|-------|----------|----------------|--------|
| ffmpeg | ffmpeg | subprocess | Shipped. 35 wiki pages, 34 CLI commands, 168 tests, 3 adversarial review rounds |
| yt-dlp | yt-dlp | subprocess | Shipped. Download from YouTube + 80 sites |
| demucs | Demucs (Meta) | Python (demucs library) | Shipped. Vocal/music separation, GPU-accelerated |
| pyannote | pyannote-audio | Python (pyannote library) | Shipped. Speaker diarization, VAD, embeddings; 94 tests + real-speech fixtures |
| qwen3-tts | Qwen3-TTS + transformers | Python (torch) | Shipped. Voice cloning, voice engineering, batch generation |
| comfyui | ComfyUI | REST API (localhost:8188) | Shipped. AI image generation; 13 model types; bundled Flux schnell sample |
| pandoc | Pandoc | subprocess | Shipped. md ↔ {pdf, docx, html, epub, latex} with citations, templates (incl. bundled Eisvogel), Lua filters; 14 wiki pages, 5 command groups, 221 tests, 3 adversarial review rounds (R1/R3+R4/R5) |

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
| rsvg-convert | librsvg | subprocess | SVG→PNG rendering for Discord embeds, visual briefs, project cards 🌶️🌶️ |
| tesseract | Tesseract OCR | subprocess | Extract text from images/screenshots. Read what Jeff pastes, process scanned docs 🌶️🌶️ |
