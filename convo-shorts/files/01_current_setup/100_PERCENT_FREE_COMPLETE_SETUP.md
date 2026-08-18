# 🎬 100% FREE YouTube Shorts Automation System
## Complete Setup Guide (Ollama + Piper + Flask + n8n)

**Goal:** Build unlimited YouTube Shorts content, zero API costs, grow channel, monetize later.

**Timeline:** 3 days to launch, 4-6 weeks to first 1,000 subscribers

---

## 📋 WHAT YOU'RE BUILDING

### The System
```
Google Sheets (Topics)
  ↓
n8n (Automation Orchestrator)
  ↓
Ollama (Free Local AI - generates scripts)
  ↓
Piper (Free Text-to-Speech - already have this)
  ↓
FFmpeg (Free Video Processing)
  ↓
Your Flask Server (Glues it all together)
  ↓
YouTube (Auto-upload your videos)
```

### Total Cost
- **API costs:** $0.00
- **Hardware needed:** Computer you have now
- **Monthly fee:** $0.00
- **Electricity:** Negligible

---

## 🎯 WHAT YOU NEED ALREADY

You told me you have:
- ✅ Ollama (installed and running)
- ✅ Flask
- ✅ Piper TTS
- ✅ YouTube API credentials
- ✅ n8n
- ✅ Computer with GPU/CPU

Perfect. We're just connecting these.

---

## 🚀 QUICK START (3 Days)

### DAY 1: Verify & Prepare (2 hours)

**Step 1: Verify Ollama**
```bash
# Terminal/Command Prompt
ollama list
# Should show installed models (mistral, etc)

# If nothing, download:
ollama pull mistral
# Takes 5-10 minutes
```

**Step 2: Verify Piper**
```bash
piper --help
# Should show help text
```

**Step 3: Verify FFmpeg**
```bash
ffmpeg -version
# Should show version info
```

**Step 4: Create Folder Structure**
```bash
# Create these folders if they don't exist:
D:\piper\
  ├── assets\backgrounds\active\
  ├── assets\backgrounds\archive\
  ├── output\
  └── temp\
```

**Step 5: Download Backgrounds**
- Find 3-5 trending short videos (YouTube, TikTok, Reddit)
- Download (look for: Subway Surfers, GTA gameplay, ASMR, nature, parkour)
- Place in: `D:\piper\assets\backgrounds\active\`
- Keep: At least 60 seconds long
- Format: MP4 (best) or MOV (convert to MP4)

**Step 6: Create Google Sheet**
- Go to: https://sheets.google.com
- Create new spreadsheet
- Name: "YouTube Shorts Pipeline"
- Set up columns (see template below)

---

### DAY 2: Setup & Test (3-4 hours)

**Step 1: Install/Update Flask Dependencies**
```bash
pip install flask requests pillow numpy opencv-python
pip install faster-whisper
```

**Step 2: Copy Server Code**
- Copy `server_ollama.py` to your `D:\piper\` folder
- Rename to `server.py` (optional, or keep as server_ollama.py)

**Step 3: Start Flask Server**
```bash
# Navigate to D:\piper\
cd D:\piper

# Start server
python server_ollama.py

# Output should show:
# 🚀 100% FREE Flask Server (Ollama + Piper + FFmpeg)
# listening on http://localhost:5000
```

**Step 4: Test Everything Works**
```bash
# In NEW terminal window:

# Test 1: Health Check
curl http://localhost:5000/health

# Should show:
# {
#   "status": "ok",
#   "ollama_running": true,
#   "piper_available": true,
#   "ffmpeg_available": true,
#   "backgrounds_available": true
# }

# Test 2: Generate Sample Script
curl http://localhost:5000/test_ollama

# This takes 2-3 minutes, should return a generated script

# Test 3: Generate Full Video
curl -X POST http://localhost:5000/generate_video \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Why we yawn",
    "category": "Weird Science",
    "video_id": "test_001"
  }'

# This takes 5 minutes, returns video path
```

**Step 5: Verify Video Generated**
- Check `D:\piper\output\` folder
- Should have `test_001.mp4` (your video!)
- Should have `test_001_thumb.jpg` (thumbnail)
- Play video, check audio is there

If all tests pass → You're ready for n8n!

---

### DAY 3: Automate with n8n (2-3 hours)

**Step 1: Create Google Sheets Credentials in n8n**
1. Open n8n (http://localhost:5000 if self-hosted)
2. Go to: Settings → Credentials → New
3. Type: Google Sheets
4. Connect your Google account
5. Name: "Google Sheets - YouTube"

**Step 2: Create YouTube OAuth in n8n**
1. Settings → Credentials → New
2. Type: OAuth 2.0
3. Name: "YouTube Upload"
4. Client ID: [from youtube_credentials.json]
5. Client Secret: [from youtube_credentials.json]
6. Scopes: `https://www.googleapis.com/auth/youtube.upload`
7. Callback: `http://localhost:5000/callback` (or n8n instance URL)
8. Click "Authorize"

**Step 3: Create n8n Workflow**
1. New Workflow
2. Add nodes in order (see detailed guide in n8n_workflow_ollama.md):

**Node 1: Cron Trigger**
- Time: 9:00 AM
- Days: Monday-Friday

**Node 2: Google Sheets Read**
- Credential: Google Sheets - YouTube
- Sheet ID: [Your sheet ID from URL]
- Sheet Name: "Topics Queue"
- Range: A:J

**Node 3: Function - Extract Today**
```javascript
const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const today = days[new Date().getDay()];
const row = $json.find(r => r['Day'] && r['Day'].trim() === today);

if (!row) {
  return { error: `No topic for ${today}` };
}

return {
  day: row['Day'],
  category: row['Category'],
  topic: row['Topic'],
  video_id: `video_${Date.now()}`
};
```

**Node 4: HTTP Request - Call Flask**
- Method: POST
- URL: `http://localhost:5000/generate_video`
- Headers: Content-Type: application/json
- Body:
```json
{
  "topic": "{{$json.topic}}",
  "category": "{{$json.category}}",
  "video_id": "{{$json.video_id}}"
}
```

**Node 5: Wait**
- Time: 5 minutes

**Node 6: HTTP Request - YouTube Upload**
- Method: POST
- URL: `https://www.googleapis.com/youtube/v3/videos?part=snippet,status`
- Headers: Authorization: Bearer {{$json.YOUTUBE_ACCESS_TOKEN}}
- Upload: Media file from `{{$json.body.video_path}}`

**Node 7: Function - Extract Video ID**
```javascript
return {
  videoId: $json.body?.id || "pending",
  youtubeUrl: `https://youtube.com/shorts/${$json.body?.id || ""}`,
  uploadTime: new Date().toISOString()
};
```

**Node 8: Google Sheets Update**
- Update the row with:
  - Status: "Done"
  - YouTube URL: `{{$json.youtubeUrl}}`

**Step 4: Test Workflow**
1. Add test topic to Google Sheet:
   ```
   Day: Monday
   Category: Weird Science
   Topic: Why you yawn
   ```

2. Click "Execute Workflow" (manual trigger)

3. Watch logs - should:
   - Read from Sheets ✓
   - Call Flask ✓
   - Wait 5 mins ✓
   - Upload to YouTube ✓
   - Update Sheets ✓

4. Check YouTube Studio for video (might take 15 mins to process)

---

## 📊 GOOGLE SHEETS SETUP

### Create These Tabs:

**Tab 1: "Topics Queue"**
```
A          B                        C                    D    E              F              G
Day        Category                 Topic                Hook Script Status Video Status   YouTube URL
Monday     Weird Science            Why you yawn               Ready          Done          youtube.com/...
Tuesday    Productivity & stoicism  Morning routine            Ready          Done          youtube.com/...
Wednesday  Human Behavior           Body language tells        Ready          Done          youtube.com/...
Thursday   Weird Science            Sleep paralysis           Blank          Blank         Blank
```

**Tab 2: "Analytics"**
```
Week       Videos   Views   Avg Watch%  Top Topic          Revenue
Week 1     4        200     30%         Weird Science      $0
Week 2     4        500     35%         Weird Science      $0
Week 3     4        1200    40%         Human Behavior     $0
```

**Tab 3: "Topics Bank"**
(For future planning - 50+ topics pre-written)
```
Category            Topic
Weird Science       Why we yawn
Weird Science       How brains forget
Productivity        Millionaire morning routine
...
```

---

## 🎯 YOUR FIRST WEEK

### Monday Morning
1. Add 4 topics to Google Sheet (Mon-Thu)
2. n8n triggers at 9 AM
3. First video generates automatically
4. Uploads to YouTube

### Tuesday-Thursday
- Same process, new topic
- You do nothing (fully automated)

### Friday Evening
1. Check YouTube Analytics
2. Note which videos got views
3. Plan next week (double down on winners)
4. Download new background videos (monthly rotation)

### Saturday-Sunday
1. Relax
2. Comment on engagement (optional)
3. Plan Week 2 topics

---

## 💡 CONTENT STRATEGY (Critical!)

### Use These 4 Topics This Week

**Monday: Weird Science**
```
Topic: Why your brain forgets names immediately
Category: Weird Science
```

**Tuesday: Productivity**
```
Topic: Why successful people wake up at 4 AM
Category: Productivity & stoicism
```

**Wednesday: Human Behavior**
```
Topic: If someone does this, they're manipulating you
Category: Human Behavior
```

**Thursday: Weird Science**
```
Topic: Your body has MORE bacteria than human cells
Category: Weird Science
```

(All from CONTENT_IDEAS_200_TOPICS.md file)

### Why This Mix?
- Variety = What works becomes clear
- 2 science, 1 productivity, 1 behavior = Balanced
- Hooks are proven to work
- Topics are highly searchable

---

## 🛠️ TROUBLESHOOTING

### Issue: Flask won't start
```
Error: Port 5000 already in use

Fix:
1. Close any other Flask instances
2. Kill process on port 5000:
   Windows: netstat -ano | findstr :5000 → taskkill /PID [PID] /F
   Mac/Linux: lsof -i :5000 → kill -9 [PID]
3. Start again: python server_ollama.py
```

### Issue: Ollama not responding
```
Error: "Ollama not accessible"

Fix:
1. Verify Ollama is running: ollama serve (in separate terminal)
2. Check port: curl http://localhost:11434/api/tags
3. If connection refused, Ollama not running
```

### Issue: Video takes too long
```
Current: 5 minutes
Desired: Faster?

Options:
1. Use faster model: ollama pull neural-chat
2. Reduce wait time in n8n (3 mins instead of 5)
3. Add GPU to computer ($150-300)
4. Reduce video quality in FFmpeg (crf 28 instead of 23)
```

### Issue: YouTube upload fails
```
Error: 401 Unauthorized

Fix:
1. OAuth token expired
2. Re-authenticate in n8n credentials
3. Grant YouTube upload permission again
4. Try again
```

### Issue: Script quality is bad
```
Ollama generating poor scripts?

Fix:
1. Change model: ollama pull llama2:13b (better quality)
2. Try: ollama pull neural-chat (balanced)
3. Adjust prompts in server_ollama.py (line ~150)
4. Change temperature: 0.7 → 0.5 (less random)
```

---

## 📈 GROWTH MILESTONES & TIMELINE

### Week 1-2
- ✓ 4-8 videos uploaded
- ✓ 0 API costs
- ✓ 100-500 views total
- Goal: Prove it works

### Week 3-4
- ✓ 8-16 videos
- ✓ 500-2,000 views
- ✓ First 50-100 subscribers
- Goal: Identify best content type

### Month 2
- ✓ 16-24 videos
- ✓ 5,000-20,000 views
- ✓ 500-1,500 subscribers
- Goal: Optimize for highest-performing topics

### Month 3
- ✓ 20-30 videos
- ✓ 20,000-50,000 views
- ✓ 1,500-5,000 subscribers
- Goal: Hit monetization requirements (1,000 subs minimum)

### Month 6
- ✓ 50-100 videos
- ✓ 100,000+ views
- ✓ 10,000+ subscribers
- ✓ **START MONETIZATION** (See MONETIZATION_REINVESTMENT_PLAN.md)
- Goal: Sustainable revenue

---

## 💰 COST BREAKDOWN

### Hardware (Already Have)
- Computer: Already owned
- GPU (optional): $0-300
- Storage: Free (only 50GB needed)

### Software (All Free)
- Ollama: $0
- Piper: $0
- FFmpeg: $0
- Faster Whisper: $0
- Flask: $0
- n8n: $0 (self-hosted)

### Hosting
- All local = $0/month

### Content (One-time)
- Background videos: $0 (download from YouTube/TikTok)

### Total Investment
**$0.00** (to launch)

---

## 🎓 LEARNING RESOURCES

- **Ollama:** OLLAMA_SETUP_GUIDE.md
- **n8n Workflow:** n8n_workflow_ollama.md
- **Content Ideas:** CONTENT_IDEAS_200_TOPICS.md
- **Monetization (later):** MONETIZATION_REINVESTMENT_PLAN.md
- **Quick reference:** QUICK_REFERENCE.md

---

## ✨ CRITICAL SUCCESS FACTORS

### Do This
- ✅ Consistent uploads (3-4x/week)
- ✅ Track performance (weekly)
- ✅ Optimize based on data (which topics work)
- ✅ Rotate backgrounds monthly (prevents repetition detection)
- ✅ Engage with comments (builds community)
- ✅ Reinvest revenue (when it comes)

### Don't Do This
- ❌ Upload 10+ videos/week (quality suffers)
- ❌ Change Ollama prompts constantly (they work)
- ❌ Use same background every video (algorithm detects)
- ❌ Expect instant growth (Week 1-2 are slow)
- ❌ Monetize too early (focus on growth first)
- ❌ Try every platform at once (master YouTube first)

---

## 🚀 NEXT STEPS

### Right Now
1. ✅ Read this document completely
2. ✅ Verify you have Ollama, Piper, FFmpeg
3. ✅ Download 3-5 background videos
4. ✅ Create Google Sheet

### Today
5. ✅ Copy server_ollama.py to D:\piper\
6. ✅ Start Flask server
7. ✅ Test with curl commands
8. ✅ Verify video generates

### Tomorrow
9. ✅ Build n8n workflow
10. ✅ Test with manual trigger
11. ✅ Add first real topic to Sheets
12. ✅ Watch first video auto-generate and upload

### This Week
13. ✅ Add 4 topics (Mon-Thu)
14. ✅ Let automation run all week
15. ✅ Check YouTube for videos
16. ✅ Note which topics get views
17. ✅ Plan Week 2 (double down on winners)

### Month 1
18. ✅ Maintain 4 videos/week
19. ✅ Track performance
20. ✅ Build to 500+ subscribers
21. ✅ Rotate backgrounds weekly
22. ✅ Optimize content based on data

---

## 💬 FINAL CHECKLIST

Before you launch:

- [ ] Ollama installed and running
- [ ] `ollama pull mistral` (or model of choice)
- [ ] Piper working (`piper --help` shows output)
- [ ] FFmpeg installed (`ffmpeg -version` works)
- [ ] Flask dependencies installed (`pip install flask requests...`)
- [ ] D:\piper\ folder structure created
- [ ] 3-5 background videos downloaded
- [ ] Google Sheet created with Topics Queue tab
- [ ] server_ollama.py copied to D:\piper\
- [ ] Flask starts without errors
- [ ] `curl http://localhost:5000/health` returns success
- [ ] `curl http://localhost:5000/test_ollama` generates script
- [ ] Manual video generation works (`curl ... /generate_video`)
- [ ] YouTube credentials file in project root
- [ ] n8n credentials set up (Google Sheets + YouTube)
- [ ] n8n workflow built with 8 nodes
- [ ] Manual workflow test successful
- [ ] Video appears in YouTube (processing)
- [ ] Results logged back to Google Sheet

**All checked?** You're ready to launch! 🚀

---

## 🎬 YOU'RE BUILDING A CONTENT EMPIRE

Remember:
- Week 1: Slow (50-200 views)
- Week 4: Growing (500-1,500 views)
- Month 2: Accelerating (2,000-5,000 views)
- Month 3: Gaining traction (5,000-20,000 views)
- Month 6: Momentum (50,000+ views/month)

**Each video you upload makes the next one easier** (algorithm learns your style, audience grows).

By Month 3, you'll have enough subscribers to monetize. By Month 6, first real income. By Month 12, sustainable business.

**Zero API costs. Infinite scale. Full control.**

Let's go. 🚀
