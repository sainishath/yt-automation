# Production Checklist — YouTube Automations

## Pipeline 1: Alternate History Shorts (Channel A)
- [x] Fix argparse string interpolation bug in `alternate-history-shorts/scripts/pipeline_runner.py` line 403
- [x] Verify local Ollama service (`http://127.0.0.1:11434`) and model `llama3.2:latest` / `qwen2.5-coder:7b`
- [x] Start and verify local Fooocus SDXL service (`http://127.0.0.1:7865`) via Gradio API
- [x] Validate audio synthesis and alignment dependencies (Edge-TTS, faster-whisper, ffmpeg)
- [x] Diagnose and fix script critic gate duration and repetitive 5-gram constraints in `generate_script.py`
- [x] Verify `generate_script.py` produces an 8.5/10 passed script with RAG claim verification
- [x] Execute `alternate-history-shorts/scripts/pipeline_runner.py` for "What if the Roman Empire never fell?" with `--no_fallback`
- [x] Verify 17/17 QA Gate passing and artifact generation in `alternate-history-shorts/output/`
- [x] Confirm proxy video generation (0.83 MB) and successful dispatch to Channel A Discord review webhook (`1528622690980724807`)
- [x] Confirm `growth.db` status updated to `AWAITING_REVIEW`

## Week 1 Flagship Documentary: The Fall of Constantinople (1453)
- [x] Install clean Fooocus SDXL v2.5.0 standalone on `D:\Projects\Fooocus_win64_2-5-0` (`D:\Projects\Fooocus`) on port 7865
- [x] Download and verify base SDXL checkpoint `juggernautXL_v8Rundiffusion.safetensors` (7.10 GB)
- [x] Implement Primary Sources Ingestion & Manuscript Card Generator (`pipeline/primary_sources.py`)
- [x] Implement Procedural Tactical Siege Map & Overland Fleet Transit Engine (`longform_engine/tactical_map_renderer.py`)
- [x] Implement Interactive Overlays: Act Badges `(X=1520, Y=60)` & Audio Ducking (`longform_engine/interactive_overlays.py`)
- [x] Implement 80-Shot Multi-Act Dispatcher & Assembler (`longform_engine/assemble_longform.py`)
- [x] Implement Mobile-Safe Subtitle Vertical Shorts Slicer (`longform_engine/short_splitter.py`)
- [x] Run full production render: 80 cinematic SDXL shots on RTX 4070 (0 cloud API spend)
- [x] Assemble master 16:9 documentary: `constantinople_1453_10min_master.mp4` (547.3s / 9.12 min, 172.6 MB)
- [x] Slice and export 5 vertical 9:16 Shorts with `MarginV=620` subtitles in `longform_engine/output/history_10min/shorts/`
- [x] Generate YouTube description, chapter timestamps, and pinned comments in `production_releases/week_01_constantinople_1453/`
- [x] Verify 36/36 tests passing in `tests/`
