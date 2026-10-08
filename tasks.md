# Production Checklist — Alternate History Video Generation

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
