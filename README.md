# YouTube Shorts Automation Engine (Dual-Pipeline Growth Intelligence Platform)

A production-grade, closed-loop YouTube Shorts generation, validation, review-gating, and empirical learning platform powering two automated channels:

1. **Pipeline 1: Chronos Shift (`alternate-history-shorts`)**  
   Groundbreaking historical "What-If" shorts with RAG v4 academic evidence grounding, Whisper word-highlight subtitles, Fooocus SDXL photorealistic rendering, Ken Burns cinematic camera motion, and Content Brain dynamic strategy bounds.
2. **Pipeline 2: Debate Protocol / Senior Dev (`convo-shorts`)**  
   High-retention software engineering and technical deep-dives with multi-angle strategic concept generation, single senior developer narration, syntax-highlighted code cards, and background gameplay integration.

---

## 🏛️ System Architecture (Content Brain v1 Closed Loop)

```mermaid
flowchart TD
    %% ==========================================
    %% LAYER 1: EXTERNAL EVIDENCE & BENCHMARKS
    %% ==========================================
    subgraph L1_EXTERNAL["LAYER 1: External Evidence & Benchmarks"]
        EXT_CORPUS[("Relational External Corpus\n(Multi-Sheet Evidence)")]
        EXT_REPO[ExternalIntelligenceRepository]
        EXT_PRIORS[External Priors Engine\n(Hypotheses & Transferability)]
        EXT_CORPUS --> EXT_REPO --> EXT_PRIORS
    end

    %% ==========================================
    %% LAYER 2: CONTENT BRAIN & STRATEGY MEMORY
    %% ==========================================
    subgraph L2_BRAIN["LAYER 2: Shared Content Brain & Strategy Memory"]
        SM[StrategyManager\n(Version Registry: v1.0, v1.1...)]
        DE[DecisionEngine\n(Hypothesis & Arm Balancing)]
        EXP_MGR[ExperimentManager\n(Arm Definitions & N>=4 Guard)]
        TOPIC_POOL[TopicPoolManager\n(Candidate Ranking)]
        CRITIC[HybridScriptCritic\n(Tier 1 Deterministic + Tier 2 Semantic Fail-Closed)]
        
        SM --> DE
        EXP_MGR --> DE
        TOPIC_POOL --> DE
        EXT_PRIORS -.->|"Priors Grounding"| DE
    end

    %% ==========================================
    %% LAYER 3: PRODUCTION PIPELINES (ISOLATED)
    %% ==========================================
    subgraph L3_PRODUCTION["LAYER 3: Production Execution (Strictly Isolated)"]
        subgraph P1["Pipeline 1: Chronos Shift (History)"]
            P1_LINEAGE[Inception Lineage Bound]
            P1_RAG[RAG v4 Evidence Retrieval]
            P1_GEN[History Script Generator\n(Dynamic Duration Bounds)]
            P1_CRIT[Hybrid Critic Quality Gate\n(3 Revision Loops / Fail-Closed)]
            P1_MEDIA[Full-Screen SDXL (Fooocus) +\nOrchestral BGM + Edge-TTS]
            P1_QA[17/17 QA Gate]
            P1_MAN[run_manifest.json]
            
            P1_LINEAGE --> P1_RAG --> P1_GEN --> P1_CRIT --> P1_MEDIA --> P1_QA --> P1_MAN
        end

        subgraph P2["Pipeline 2: Debate Protocol (Coding)"]
            P2_LINEAGE[Inception Lineage Bound]
            P2_ANGLES[p2_multi_angle.py\n(Strategic Angle Generator)]
            P2_GEN[Senior Dev Script Generator\n(Code Snippets & Architecture)]
            P2_CRIT[Hybrid Critic Quality Gate\n(3 Revision Loops / Fail-Closed)]
            P2_MEDIA[Centered 810x810 Fooocus Overlay +\nMinecraft Gameplay BG + Piper TTS]
            P2_QA[Audio LUFS & Visual QA Gate]
            P2_MAN[*.manifest.json]
            
            P2_LINEAGE --> P2_ANGLES --> P2_GEN --> P2_CRIT --> P2_MEDIA --> P2_QA --> P2_MAN
        end

        DE --> P1_LINEAGE
        DE --> P2_LINEAGE
        P1_CRIT --- CRITIC
        P2_CRIT --- CRITIC
    end

    %% ==========================================
    %% LAYER 4: HUMAN GATE & OBSERVABILITY
    %% ==========================================
    subgraph L4_OBSERVABILITY["LAYER 4: Human Gate & Snapshot Observability"]
        DISCORD{Discord Proxy Review\n(Human Gate: 540x960 Proxy)}
        YT[(YouTube Channel Deployment\nPrivate Status Default)]
        COLLECTOR[AnalyticsCollector\n(YouTube API / Token Auth)]
        SNAPS[(performance_snapshots\n1h, 6h, 24h, 48h, 7d Windows)]
        
        P1_MAN --> DISCORD
        P2_MAN --> DISCORD
        DISCORD -- "Approved" --> YT
        YT --> COLLECTOR --> SNAPS
    end

    %% ==========================================
    %% LAYER 5: LEARNING & CLOSED LOOP FEEDBACK
    %% ==========================================
    subgraph L5_LEARNING["LAYER 5: Empirical Growth Learning Loop"]
        AUTOPSY[Video Autopsy Analyzer\n(Causal Attribution & Features)]
        LE[LearningEngine\n(Batch Learning Cycle)]
        N_CHECK{"N >= 4 mature samples\nper arm?"}
        STAT_EVAL[Statistical Experiment Evaluation\n(Welch's t-test Significance)]
        OUTCOME_CHECK{"Statistically\nsignificant winner?"}
        FPD[First-Party Dominance Override\n(Overrides External Priors)]
        DELTA[Immutable Strategy Version Delta\n(e.g., channel_a_strategy_v1.1.json)]
        RETAIN[Retain Existing Strategy\n& Continue Observation]
        
        SNAPS --> AUTOPSY --> LE
        SNAPS --> LE
        LE --> N_CHECK
        N_CHECK -- "No (N < 4)" --> HOLD[Status: INSUFFICIENT_DATA\nCollect More Observations]
        N_CHECK -- "Yes (N >= 4)" --> STAT_EVAL --> OUTCOME_CHECK
        OUTCOME_CHECK -- "No" --> RETAIN
        OUTCOME_CHECK -- "Yes" --> FPD
        OUTCOME_CHECK -- "Yes" --> DELTA
    end

    %% ==========================================
    %% CLOSED-LOOP FEEDBACK ARROWS
    %% ==========================================
    DELTA ==>|"Evolves Active Strategy Version"| SM
    FPD -.->|"Updates Prior Status / Weight"| EXT_PRIORS
```

---

## 🚀 Quick Start (Starting Production Daemons)

### 1. Prerequisites
- Python 3.10+
- FFmpeg installed & on system PATH
- Ollama running locally (`http://127.0.0.1:11434`)
- Fooocus SDXL running locally (`http://127.0.0.1:7865`)
- n8n running locally (`http://127.0.0.1:5678`)

### 2. Launching Servers

```powershell
# In PowerShell (with UTF-8 encoding enabled):
$env:PYTHONIOENCODING="utf-8"

# Terminal 1 — Start Pipeline 1 Server (Port 8000):
python alternate-history-shorts/server_alt_history.py

# Terminal 2 — Start Pipeline 2 Server (Port 5001):
python convo-shorts/yt-automation-engine/server.py
```

---

## 📋 Production Endpoints & CLI Entrypoints

### Pipeline 1 (Alternate History)
- **Health Check:** `GET http://127.0.0.1:8000/health`
- **Trigger Generation:** `POST http://127.0.0.1:8000/generate-alternate-history`
- **Status Check:** `GET http://127.0.0.1:8000/get-status?id=<video_id>`
- **Video Download:** `GET http://127.0.0.1:8000/get-video?id=<video_id>`
- **YouTube Upload:** `POST http://127.0.0.1:8000/upload-youtube`
- **CLI Runner:**
  ```powershell
  python alternate-history-shorts/scripts/pipeline_runner.py --topic "What if the Library of Alexandria never burned?" --video_id "alexandria_01"
  ```

### Pipeline 2 (Convo Shorts)
- **Next Topic:** `GET http://127.0.0.1:5001/get-next-topic`
- **Trigger Generation:** `POST http://127.0.0.1:5001/tts`
- **Discord Review:** `POST http://127.0.0.1:5001/post-discord-review`
- **YouTube Upload:** `POST http://127.0.0.1:5001/upload_youtube`
- **CLI Runner:**
  ```powershell
  python convo-shorts/yt-automation-engine/main.py --topic "Why your brain forgets names" --category "Weird Science"
  ```

---

## ⚡ Orchestration & n8n Workflows

- **Pipeline 1 Active Workflow:** `Alternate History Shorts — Production Pipeline with Discord Review Gate` (`ID: xAyYyalPutEsTsDb`)
- **Pipeline 2 Active Workflow:** `YT Shorts Automation with Discord Review Gate` (`ID: N3DelK9B5ssN879H`)
- **Workflow Canonical Definitions:**
  - Pipeline 1: [`alternate-history-shorts/n8n-workflows/alternate_history_production.json`](file:///d:/Projects/yt-automations/alternate-history-shorts/n8n-workflows/alternate_history_production.json)
  - Pipeline 2: [`convo-shorts/n8n_youtube_shorts_workflow.json`](file:///d:/Projects/yt-automations/convo-shorts/n8n_youtube_shorts_workflow.json)

---

## 📚 Detailed Documentation Suite

- 📈 [**90-Day Channel Strategy & Monetization**](file:///d:/Projects/yt-automations/docs/channel-strategy.md): Positioning, content pillars, audience profiles, 90-day rollout roadmap, and hook scoring.
- 🏛️ [**Production Architecture & Channel Separation**](file:///d:/Projects/yt-automations/docs/production-architecture.md): Decoupled dual-channel architecture, OAuth credential isolation, and Candidate A motion freeze.
- 📖 [**Operations & Troubleshooting Manual**](file:///d:/Projects/yt-automations/docs/operations.md): Daemon startup, Discord review operations, dry-run procedures, and failure recovery.
- 🛡️ [**YouTube Monetization & Compliance Policy**](file:///d:/Projects/yt-automations/docs/monetization-policy.md): YPP guidelines, synthetic media disclosures, anti-repetition architecture, and copyright safety.
- 🔒 [**Security & Secret Governance**](file:///d:/Projects/yt-automations/docs/security.md): Zero-secret commitment rules, credential scanning, and `.gitignore` governance.

---

## 🛡️ Production Verification Suite

To run the complete 21-axis production verification suite:
```powershell
$env:PYTHONIOENCODING="utf-8"
python verify_release.py
```

Expected result: **21/21 PASS (0 failures, 0 warnings)**.
