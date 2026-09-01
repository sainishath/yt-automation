# GEMINI RESEARCH PROMPT: CODING & TECH COMPETITOR INTELLIGENCE

## Goal
Conduct structured public research on 30–100 public YouTube Shorts from top-performing, normal-performing, and lower-performing Coding, Software Engineering, AI, and Tech Education channels.

## Instructions
1. Find public YouTube Shorts in the following domains:
   - Python / JavaScript / C++ / Java / Rust / Go / SQL programming
   - Data structures, algorithms, and software engineering mental models
   - Git, Docker, Linux, APIs, databases, web development
   - Machine Learning, Neural Networks, LLMs, AI agents, RAG concepts
   - Developer productivity, coding mistakes, and tech news
2. Collect **ONLY publicly observable information**.
3. **DO NOT FABRICATE TRANSCRIPTS**. If the full video captions are unavailable, write `UNAVAILABLE`.
4. **DO NOT INVENT OR FABRICATE PRIVATE ANALYTICS**. Never guess or include CTR, retention curves, APV, swipe-away rate, or subscriber gains per video.
5. Provide the output as a clean **CSV / TSV table** (comma or tab separated) formatted according to the specification below.

---

## Canonical Table Headers & Types

| Header | Description | Example |
| :--- | :--- | :--- |
| `channel_name` | Public display name of creator/channel | `Fireship` |
| `channel_url` | Public YouTube channel URL or @handle | `https://www.youtube.com/@Fireship` |
| `public_subscriber_count` | Publicly visible subscriber count | `3100000` |
| `video_title` | Exact public video title | `Python Decorators in 100 Seconds` |
| `youtube_url` | Full public YouTube Short URL | `https://www.youtube.com/shorts/rPq5-5z_2fE` |
| `video_id` | 11-character YouTube video ID | `rPq5-5z_2fE` |
| `published_at` | Upload timestamp (ISO or YYYY-MM-DD) | `2024-02-15` |
| `duration_seconds` | Video length in seconds | `58.0` |
| `views` | Total public view count | `1450000` |
| `likes` | Total public like count (or empty if hidden) | `92000` |
| `comments` | Total public comment count (or empty if turned off) | `1400` |
| `transcript_status` | Status: `OFFICIAL_CAPTIONS`, `AUTO_GENERATED`, `CREATOR_PROVIDED`, `UNAVAILABLE` | `OFFICIAL_CAPTIONS` |
| `transcript` | Full verbatim captions text (or empty if UNAVAILABLE) | `"Python decorators allow you to wrap another function..."` |
| `performance_class` | Claimed tier: `HIGH_PERFORMER`, `NORMAL_PERFORMER`, `LOW_PERFORMER` | `HIGH_PERFORMER` |
| `relative_performance` | Claimed ratio vs channel average | `2.4` |
| `selection_reason` | Why this video was selected | `Clear analogy-first decorator explanation with rapid pace` |
| `uncertainties` | Semicolon-separated caveats / observable limitations | `High subscriber baseline; visual speed difficult to replicate` |

---

## Output Format
Generate the output as strict **CSV text** with quoted strings for fields containing commas.
