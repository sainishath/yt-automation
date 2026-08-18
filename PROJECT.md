# Project: yt-automations separation and build

## Architecture
This project consists of two separate automated YouTube Shorts pipelines:
1. **alternate-history-shorts** (formerly fooocus-yt-automation): A preserved, read-only automation pipeline generating history-whatif shorts.
2. **convo-shorts** (formerly piper-yt-automation): A two-persona debate pipeline that automates:
   - Script generation with Ollama using a specified JSON schema.
   - Dual-voice speech generation with Piper (per-line duration measured via ffprobe).
   - Video generation utilizing:
     - Continuously looped/trimmed gameplay background footage in the lower zone.
     - Fooocus image generation changing dynamically per segment/topic block in the upper zone.
     - Sidechain ducking of background music under speech.
     - Dual-colored (Cyan/Magenta) subtitles in the lower zone based on the active speaker.

### Dual-Channel n8n Workflows & Google Credentials
The production pipeline utilizes two distinct Google OAuth2 accounts in n8n for independent YouTube management:
- **Alternate History Pipeline**: Linked to **Google Account 1** (`youtube_oauth2_alternate_history`) for publishing historical what-if content (`alternate_history_pipeline.json`).
- **Factual Discussions Pipeline**: Linked to **Google Account 2** (`youtube_oauth2_factual_discussions`) for publishing scientific debate content (`factual_discussions_pipeline.json`).
- **Unified Router Workflow**: [`master_video_production_pipeline.json`](file:///d:/Projects/yt-automations/alternate-history-shorts/n8n-workflows/master_video_production_pipeline.json) routes incoming jobs dynamically by `content_type` to their respective generation stage and YouTube channel credential.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Rename & Verify Alternate History Shorts | Rename fooocus-yt-automation to alternate-history-shorts and verify executability | None | DONE |
| 2 | Rename Piper Automation | Rename piper-yt-automation to convo-shorts | None | DONE |
| 3 | Build convo-shorts Pipeline | Implement script gen, voice gen, background looping, Fooocus images, ducking mixing, split-screen canvas | M2 | DONE |
| 4 | Separate n8n Workflows | Build and configure separate n8n workflows for both pipelines | M1, M3 | DONE |
| 5 | Output Generation & Separation Report | Produce output videos and separation report | M4 | DONE |

## Interface Contracts
### convo-shorts Script Format (Ollama JSON Schema)
```json
{
  "lines": [
    {
      "speaker": "A" | "B",
      "text": "The spoken content",
      "visual_topic_prompt": "Topic keyword/prompt for Fooocus image generation"
    }
  ]
}
```

### Voice Config Schema (config/voice.json)
```json
{
  "speaker_A": {
    "model": "path/to/model",
    "config": "path/to/config"
  },
  "speaker_B": {
    "model": "path/to/model",
    "config": "path/to/config"
  }
}
```

## Technical Guidelines
### Gradio Client API Integration
When interacting with Gradio APIs (e.g., Fooocus), do not rely on standard synchronous client `.predict()` calls. Instead, query the API components config (`client.config['components']`), build arguments dynamically, set inputs via parameters setter (`fn_index=67`), and submit the generation job asynchronously (`client.submit(fn_index=68)`) in a wait-loop.

### Windows Encoding Safety
Always prefix Python commands with environment settings to prevent CP1252/UnicodeEncodeError failures.
- PowerShell: `$env:PYTHONIOENCODING="utf-8"; python ...`
- CMD: `set PYTHONIOENCODING=utf-8 && python ...`

### n8n Cache Lifecycle Management
Do not update n8n workflow connections or status directly via postgres SQL operations. Always push workflow schema changes using the n8n REST API (`PUT /api/v1/workflows/{id}`) to invalidate active in-memory caches. Use the appropriate activate/deactivate POST endpoints to toggle runtime state.
