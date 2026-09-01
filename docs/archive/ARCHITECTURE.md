# Technical Architecture: Dual-Pipeline YouTube Automation

---

## 1. Pipeline Independence Contract

Both pipelines operate as **completely decoupled, standalone production systems**:

- **Pipeline 1 (`alternate-history-shorts`)** owns its own RAG engine, script generator, Edge-TTS synthesis, Whisper alignment, Fooocus SDXL prompt builder, video assembler (Candidate A Ken Burns motion), metadata engine, Discord review client, and YouTube uploader.
- **Pipeline 2 (`convo-shorts`)** owns its own dialogue generator, co-host balance analyzer, dual Piper/Edge TTS engine, background gameplay selector, subtitle generator, thumbnail creator, Discord review client, and YouTube uploader.
- **Zero Cross-Pipeline Imports:** Scanned by automated verification (`verify_release.py`), ensuring violations = 0.

---

## 2. Pipeline 1: Alternate-History Shorts Engine

```text
[Topic Input]
     │
     ▼
[Stage 1: RAG v4 Academic Grounding]
  ├── Wikipedia API & OpenAlex API Entity Search
  ├── Source Citations & Atomic Historical Facts
  ├── Visual Evidence Extraction (Materials, Architecture, Clothing, Tools)
  └── Sufficiency Gate (Rejects fictional/non-existent subjects with INSUFFICIENT status)
     │
     ▼
[Stage 2: Script Generation & Claim Verification]
  ├── Ollama (Llama 3.1/3.2) Hook-Optimized Script Writing
  ├── Spoken Hook Generation (Scene 0 counterfactual active framing)
  └── Fact-Checking Engine: 100% atomic claim verification against evidence packet (0 Unsupported Claims)
     │
     ▼
[Stage 3: Audio Synthesis & Word-Level Alignment]
  ├── Edge-TTS Neural Voice Generation (ChristopherNeural / GuyNeural)
  └── Whisper ASR DTW Word-Level Alignment & Timing Cache
     │
     ▼
[Stage 4: Semantic Visual Planner]
  ├── Semantic Beat Planning from Narration Pauses & Timings
  └── Injection of RAG Visual Evidence into Prompts
     │
     ▼
[Stage 5: Fooocus SDXL Generation]
  ├── Async Queue Parameter Setter (fn_index=67) & Job Submitter (fn_index=68)
  └── 1080x1920 Native SDXL Photorealistic Assets
     │
     ▼
[Stage 6: Video Assembly & Subtitles]
  ├── Candidate A Ken Burns Camera Motion (8% linear zoom/pan with top-left anchoring)
  ├── 1080x1920 Native ASS Karaoke Word-Highlight Subtitles
  ├── Background Music Mixing (-22 dB ducked)
  └── FFmpeg Libx264 25 FPS Compilation
     │
     ▼
[Stage 7: YouTube Metadata & Thumbnail]
  └── High-CTR Topic-Aligned Title, Description, and Tag Generation
     │
     ▼
[Stage 8: 17-Point QA Verification Gate]
  └── Enforces 1080x1920, 25fps, H.264/AAC, 30-60s duration, 0 unsupported claims, 0 beat gaps
```

---

## 3. Pipeline 2: Conversational Debate Shorts Engine

```text
[Topic Queue / Input]
     │
     ▼
[Stage 1: Script & Dialogue Engine]
  ├── Ollama Two-Host Script Generation
  ├── Speaker B Co-Host Balance Validation (35–60% word share)
  └── Factual Claim Severity & Outro Turn Validation (≤ 25 words)
     │
     ▼
[Stage 2: Multi-Speaker Voiceover & Subtitles]
  ├── Piper ONNX / Edge-TTS Voice Generation
  └── Word-Level SRT/ASS Subtitle Generation
     │
     ▼
[Stage 3: Visual Proofs & Gameplay Compositing]
  ├── Fooocus SDXL Segment Visual Cards
  └── 60 FPS Subway Surfers / Minecraft Gameplay Background Cropping & Looping
     │
     ▼
[Stage 4: Thumbnail & Metadata Generation]
  ├── High-Contrast Debate Title Card Generation (Pillow)
  └── Viral Title, Description, and Hashtags
     │
     ▼
[Stage 5: Multi-Axis QA Gate]
  └── Enforces 1080x1920 60fps, volume normalization (-35dB to -0.5dB), duration, and rights
```

---

## 4. Orchestration & Safety Gates

1. **Discord Review Gate:**  
   Every generated video is encoded to a compact 540x960 review proxy and posted to Discord with approval/rejection commands.
2. **Rejection Safety:**  
   If rejected, workflow execution stops immediately with zero retries or loops.
3. **Idempotent YouTube Publishing:**  
   `upload_video.py` and `uploader.py` check `metadata.json` and daily quota trackers before uploading, preventing duplicate uploads on workflow retries.
