# YouTube Shorts Pipeline - Google Sheets Setup

## Sheet 1: "Topics Queue"
This is where you add topics. n8n will read from here.

| Column | Purpose | Example |
|--------|---------|---------|
| A | Day | Monday |
| B | Category | Weird Science |
| C | Topic | Why your brain forgets names (neuroscience) |
| D | Hook (AI Generated) | *Leave blank - Gemini fills this* |
| E | Script Status | Ready / In Progress / Done |
| F | Video Status | Generated / Uploaded / Published |
| G | YouTube URL | *Auto-filled after upload* |
| H | Views (24h) | *Manual check after 24 hours* |
| I | Avg View Duration | *Manual check* |
| J | Notes | Performance notes |

---

## Sheet 2: "Content Guidelines" 
Reference document for you (not for n8n):

### Weird Science Facts
- **Duration:** 25-35 seconds
- **Hook Examples:** 
  - "Your brain does THIS every night (you didn't know)..."
  - "Scientists just discovered THIS about sleep..."
  - "This one fact will change how you think..."
- **Structure:** Hook → Surprising fact → Brain science explanation → CTA
- **Tone:** Curious, mind-blowing, educational

### Productivity & Stoicism
- **Duration:** 30-40 seconds
- **Hook Examples:**
  - "Millionaires do THIS every morning..."
  - "The stoics knew this 2000 years ago..."
  - "One habit that changed everything..."
- **Structure:** Hook → The principle → Real-world example → CTA
- **Tone:** Motivational, practical, wise

### Human Behavior
- **Duration:** 25-35 seconds
- **Hook Examples:**
  - "If someone does THIS, they're manipulating you..."
  - "Your body language reveals THIS..."
  - "This psychology trick works 9/10 times..."
- **Structure:** Hook → The behavior/signal → What it means → CTA
- **Tone:** Intriguing, revealing, conversational

---

## Sheet 3: "Performance Analytics"
Track which content types convert best (fill weekly):

| Content Type | Avg Views (7d) | Avg Watch % | Avg CTR | Best Hook Type |
|--------------|----------------|-------------|---------|-----------------|
| Weird Science | | | | |
| Productivity | | | | |
| Human Behavior | | | | |

---

## How to Use:
1. **Monday morning:** Add 4 topics to "Topics Queue" (one per day Mon-Thu)
2. **n8n triggers:** Reads from "Topics Queue" daily at 9 AM
3. **Gemini generates:** Scripts + hooks
4. **Flask processes:** Video creation
5. **YouTube uploads:** Automatic
6. **You update:** Views/Watch duration every evening (copy from YouTube Analytics)
7. **Friday:** Review what worked, plan next week

---

## Pro Tips:
- **Batching:** Write all 4 topics on Monday, then let automation run
- **Testing:** First 2 weeks, upload at different times (10am, 2pm, 6pm) to find your audience's peak
- **Trending topics:** Check Reddit (r/psychology, r/science), TikTok trending sounds for ideas
- **Rotation:** Try to balance topics (not 4 science videos in a row)
