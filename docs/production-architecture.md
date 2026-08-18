# Production Architecture & Channel Separation Specification

---

## 🏛️ 1. Dual-Channel Decoupled Topology

Each pipeline operates as an **independent, isolated production engine** connected to its own dedicated YouTube channel and OAuth profile.

```text
                                [ n8n Automation Server (Port 5678) ]
                                    │                           │
                 Workflow: xAyYyalPutEsTsDb           Workflow: N3DelK9B5ssN879H
                                    │                           │
                                    ▼                           ▼
                 [ Pipeline 1 Server (Port 8000) ]     [ Pipeline 2 Server (Port 5001) ]
                 (Alternate History Engine)            (Conversational Debate Engine)
                                    │                           │
                                    ▼                           ▼
                        [ Discord Review Gate ]     [ Discord Review Gate ]
                                    │                           │
                            (Human Approval)            (Human Approval)
                                    │                           │
                                    ▼                           ▼
                   [ Pipeline 1 YouTube Auth ]         [ Pipeline 2 YouTube Auth ]
                   Profile: CHANNEL_A_PROFILE          Profile: CHANNEL_B_PROFILE
                   (token.json / client_secrets)       (youtube_token.pickle / creds)
                                    │                           │
                                    ▼                           ▼
                   ╔═════════════════════════╗         ╔═════════════════════════╗
                   ║  CHANNEL A (History)    ║         ║  CHANNEL B (Debates)    ║
                   ║  "Chronos Shift"        ║         ║  "Debate Protocol"      ║
                   ╚═════════════════════════╝         ╚═════════════════════════╝
```

---

## 🔑 2. Channel Credential Separation Architecture

To guarantee that each pipeline uploads exclusively to its intended destination channel, credential resolution is segregated:

### Pipeline 1: Channel A Configuration
- **Default Directory:** `alternate-history-shorts/config/`
- **Secrets File:** `client_secrets.json` (configurable via `P1_YOUTUBE_CLIENT_SECRETS`)
- **Token File:** `token.json` (configurable via `P1_YOUTUBE_TOKEN`)
- **OAuth Callback Port:** Dynamic / Port 8080
- **Quota Tracker:** `alternate-history-shorts/config/quota_tracker.json`

### Pipeline 2: Channel B Configuration
- **Default Directory:** `convo-shorts/config/` or `convo-shorts/yt-automation-engine/`
- **Secrets File:** `youtube_credentials.json` (configurable via `P2_YOUTUBE_CLIENT_SECRETS`)
- **Token File:** `youtube_token.pickle` (configurable via `P2_YOUTUBE_TOKEN`)
- **OAuth Callback Port:** Port 8090
- **Quota Tracker:** Handled via video manifest tracking and task database

---

## 🎬 3. Frozen Quality & Motion Baseline

### Pipeline 1 (Alternate History Shorts)
- **Camera Motion:** **Candidate A (8% linear Ken Burns zoom and 86.4px pan, top-left anchor)** is permanently frozen. No experimental cosine or supersampled smoothers are permitted.
- **Visual Engine:** Fooocus SDXL photorealistic rendering at 1080x1920 native aspect ratio.
- **Audio Alignment:** Whisper DTW word-level alignment driving ASS word-highlight karaoke subtitles.
- **RAG & Claims:** Academic historical grounding with strict `0 unsupported claims` QA gate.

### Pipeline 2 (Conversational Debate Shorts)
- **Dialogue Engine:** Multi-turn host dialogue balancing Speaker A and Speaker B (35–60% word distribution).
- **Outro Word Limit:** Enforced at $\le 25$ words to prevent abrupt audio cutoffs.
- **Media Compositing:** High-retention gameplay background integration with synchronized subtitle overlays.
