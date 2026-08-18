# Original User Request

## Initial Request — 2026-07-12T18:19:12+05:30

We are separating and building two distinct automated video pipelines:
1. **Pipeline 1: alternate-history-shorts** (existing, verified history-whatif-pipeline. MUST NOT BE MODIFIED).
2. **Pipeline 2: convo-shorts** (new conversation/debate style short generator with Piper dual-voices, split upper/lower layout, Whisper-aligned captions, and subway-surfers gameplay backgrounds).

Working directory: D:\Projects\yt-automations

## Requirements

### R1. Alternate History Shorts Preservation
- Rename `fooocus-yt-automation` to `alternate-history-shorts` and ensure its files (`generate_script.py`, `generate_audio.py`, `generate_images.py`, `assemble_video.py`, `rag_grounding.py`) and configurations remain unmodified and fully functional.

### R2. Conversation Debate Pipeline (Convo Shorts)
- Rename `piper-yt-automation` to `convo-shorts` and build a separate, independent debate video generator inside it.
- **Script Generation:** Ollama generates two-persona debate script (JSON schema: `{"lines": [{"speaker": "A"|"B", "text": "...", "visual_topic_prompt": "..."}]}`).
- **Voice Generation:** Piper TTS per line using two distinct voice configurations (configured in `/config/voice.json` per persona), measuring actual duration using `ffprobe`.
- **Gameplay Background:** Pull clips from a local folder of self-recorded or clearly licensed / royalty-free gameplay footage (`/gameplay/`), looped and trimmed to match the total video duration.
- **Image Cadence:** Generate topic-relevant Fooocus images to change per topic/segment (changing less frequently than captions, timed to match speaker segments).
- **Audio Mixing:** Mix background lo-fi music with sidechain ducking compression (music ducked when voices are active).
- **Canvas Layout:** Vertical 1080x1920 canvas split into:
  - Upper zone (1080x960): Topic-relevant generated Fooocus image, scaled/cropped to fill this zone cleanly.
  - Lower zone (1080x960): Gameplay footage playing continuously with subtitles.

## Acceptance Criteria

### Verification Checks
- [ ] Alternate history shorts files are untouched and fully executable.
- [ ] Convo shorts pipeline compiles a test script of 3-4 exchanges into a split-screen 1080x1920 video.
- [ ] Captions are positioned exclusively in the lower zone and visually distinguished by speaker color (e.g. Cyan for Speaker A, Magenta for Speaker B).
- [ ] Background music ducks automatically when speech is active (sidechain compression).
- [ ] Upper zone image successfully changes per segment/topic block.
