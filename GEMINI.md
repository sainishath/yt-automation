# Project Antigravity Rules — YouTube Automations

## 1. Dual-Pipeline Architecture & Strict Isolation
- **Pipeline 1 (`alternate-history-shorts` / Channel A / Chronos Shift):**
  - Must always be invoked via `alternate-history-shorts/scripts/pipeline_runner.py`.
  - 100% full-screen 9:16 cinematic SDXL visuals with Ken-Burns pan/zoom movement.
  - Zero Minecraft or gameplay footage.
  - Narrator: Single authoritative documentary voice (`en-US-ChristopherNeural`, Edge-TTS) with orchestral BGM.
  - Discord Review Webhook: `1528622690980724807`.
- **Pipeline 2 (`convo-shorts` / Channel B / Debate Protocol):**
  - Must always be invoked via `convo-shorts/yt-automation-engine/main.py`.
  - Full-screen retentive gameplay background (Minecraft/Subway Surfers) with centered upper-zone 896x896 Fooocus image overlays.
  - Dual Piper synthetic voices (Host A - Ryan, Host B - Amy).
  - Female voice pacing is permanently locked at `length_scale: 0.95` (~195 WPM).
  - Discord Review Webhook: `1528609697089982494`.
- **Strict Invariant:** Neither pipeline shall ever import, call, or share video assembly wrappers from the other.

## 2. Image Generation & Fooocus SDXL Invariant
- All visual scenes and overlays MUST be generated using local Fooocus SDXL on `http://127.0.0.1:7865`.
- **Zero External Image API Calls:** Never fall back to external APIs (Gemini/Nano/Banana/DALL-E) or consume cloud image API keys.
- If local Fooocus is unavailable, halt production immediately and prompt the user to ensure the local Fooocus service or Docker container is active on port 7865.

## 3. Human Gate & Discord Review Approval
- Every video generation must pass multi-axis QA (17/17 for Channel A, 16/16 for Channel B) and generate a `540x960` proxy.
- Proxies must be posted to the channel's respective Discord webhook.
- Never upload videos to YouTube automatically without explicit Discord human approval or direct user confirmation.

## 4. Empirical Growth Intelligence ($N \ge 4$)
- First-party empirical metrics strictly dominate external priors.
- Strategy promotions and experiment decisions require $N \ge 4$ mature samples per arm (7-day maturity).
