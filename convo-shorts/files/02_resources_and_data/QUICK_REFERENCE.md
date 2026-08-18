# ⚡ QUICK REFERENCE CHEAT SHEET

## 📅 DAILY WORKFLOW (Monday-Thursday)

### 9:00 AM (Automated)
```
✓ n8n reads Google Sheets
✓ Gemini generates script
✓ Piper creates audio
✓ Flask generates video
✓ Video uploads to YouTube
✓ Results logged to Sheets
→ You do nothing (unless something breaks)
```

### Evening (5 min check)
```
1. Open YouTube Studio
2. Check if video processed
3. Check initial view count (if > 0 views, good sign)
4. Note any errors in n8n logs
```

---

## 📋 WEEKLY CHECKLIST (Sunday Night)

### What to Do:
```
[ ] Add 4 topics to Google Sheet (Monday-Thursday)
[ ] Verify backgrounds folder has 3-5 videos
[ ] Check previous week's performance
[ ] Plan next week's topics based on what worked
```

### What NOT to Change:
```
✗ Don't modify Gemini prompts (they work)
✗ Don't change video settings (1.15x speed is optimal)
✗ Don't upload manually (breaks the data pipeline)
```

---

## 🎯 MONTHLY CHECKLIST (Last Friday)

### Backgrounds Rotation:
```
1. Download 3-5 NEW trending videos
2. Move them to: D:\piper\assets\backgrounds\active\
3. Move old videos to: D:\piper\assets\backgrounds\archive\
4. Delete 2+ month old videos from archive (save space)
```

### Analytics Review:
```
1. Open YouTube Analytics
2. Check top 3 videos by views
3. Check average watch duration
4. Update "Performance Analytics" sheet
5. Decide: More of X topic? Less of Y topic?
```

### Prompt Refinement (Optional):
```
If your videos aren't getting good hooks:
1. Open gemini_prompts.py
2. Try different hook templates
3. Test with 1-2 videos
4. Keep what works, discard what doesn't
```

---

## 🚨 EMERGENCY TROUBLESHOOTING

### "No video uploaded today"
**Check in order:**
1. Is Flask running? → `python server.py`
2. Are backgrounds available? → Check `D:\piper\assets\backgrounds\active\`
3. Check n8n logs for error messages
4. Manually test Flask: `curl http://localhost:5000/health`

### "Video is blank/no audio"
1. Check YouTube processing (takes 15 mins sometimes)
2. Check video file size > 10MB → Download from output folder
3. Check if Piper voice is crashing → Try different voice
4. Resync audio: `ffmpeg -i video.mp4 -c:v copy -c:a aac final.mp4`

### "Captions are misaligned"
1. Check audio speed in Gemini_prompts (should be 1.15x)
2. Check Whisper transcription: Are timings correct?
3. Regenerate with different background (variable video lengths)

### "n8n won't connect to Flask"
1. Flask running? → `python server.py`
2. Correct URL? → Should be `http://localhost:5000/generate_video`
3. Port blocked? → Try different port (change in server.py line 500)

### "YouTube upload fails with 401"
1. OAuth token expired → Re-authenticate in n8n credentials
2. Grant YouTube upload permission again
3. Check YouTube API quota isn't exceeded

---

## 📊 PERFORMANCE TARGETS

### Week 1-2 (Baseline)
- Upload consistency: 4/4 videos ✓
- Avg views per video: 200-500
- Watch duration: 30%+
- Goal: Just get it working

### Week 3-4 (Optimization)
- Avg views: 500-1,500
- Watch duration: 35%+
- CTR: 2-3%
- Goal: Identify best topics

### Month 2+
- Avg views: 1,500-5,000+
- Watch duration: 40%+
- CTR: 3-5%
- Goal: Scale and dominate niche

---

## 🎬 VIDEO NAMING CONVENTION

Your Flask server auto-generates names, but for manual uploads:
```
video_[DATE]_[CATEGORY]_[TOPIC].mp4

Example:
video_20260422_WeirdScience_BrainYawn.mp4
video_20260423_Productivity_ColdShowers.mp4
```

---

## 🔑 KEY FILE LOCATIONS

```
D:\piper\
├── server_enhanced.py          ← Flask server
├── youtube_credentials.json    ← OAuth file
├── assets\
│   └── backgrounds\
│       ├── active\             ← Current videos (edit weekly)
│       └── archive\            ← Old videos (don't touch)
├── output\                     ← Generated videos (download if needed)
├── temp\                       ← Temporary files (safe to delete)
└── config.json                 ← Optional: points to backgrounds folder
```

---

## 🔗 IMPORTANT LINKS

```
Google Sheets:
→ https://docs.google.com/spreadsheets/d/[YOUR_SHEET_ID]/

YouTube Studio:
→ https://studio.youtube.com/

n8n Workflow:
→ http://localhost:5000 (if self-hosted)

YouTube Analytics:
→ https://studio.youtube.com/analytics/overview
```

---

## 🛠️ COMMON COMMANDS

```bash
# Start Flask server
python server.py

# Check if server is running
curl http://localhost:5000/health

# View Flask logs (Windows)
python server.py 2>&1 | findstr "error"

# View Flask logs (Mac/Linux)
python server.py 2>&1 | grep error

# Test Piper
echo "Hello world" | piper --voice en_US-hfc_female-medium --output_file test.wav

# Clear temp files
rm -r D:\piper\temp\*

# Check YouTube quota
curl -H "Authorization: Bearer [TOKEN]" \
  https://www.googleapis.com/youtube/v3/i18nRegions?part=snippet
```

---

## 💡 PRO QUICK TIPS

**For Faster Results:**
- Pre-write topics 2 weeks in advance
- Batch-test hooks (write 10, see which resonates)
- Use trending audio in background videos
- Respond to top comments with AI-generated responses

**To Avoid Burnout:**
- Don't obsess over daily views (check weekly)
- Don't re-record videos (move forward, not backward)
- Don't copy bigger channels (find your angle)
- Don't upload more than 4x/week (quality > quantity)

**To Stay Ahead:**
- Track trending topics from Reddit/TikTok
- Monitor competitor content (but don't copy)
- A/B test hooks with similar topics
- Ask audience what they want (via community posts)

---

## ⚠️ DO NOT DO THIS

```
✗ Don't manually rename videos (breaks pipeline)
✗ Don't delete temp files while server is running
✗ Don't change YouTube credentials mid-week
✗ Don't edit Google Sheet headers (breaks n8n)
✗ Don't use same topic twice in same month
✗ Don't upload without letting background process finish
✗ Don't have Flask & n8n both trying to upload (one only)
```

---

## 🆘 IF SOMETHING BREAKS

**Step 1:** Restart
```bash
# Kill Flask
Ctrl+C (if running in terminal)

# Restart n8n workflow
Stop → Wait 10s → Start

# Restart Flask
python server.py
```

**Step 2:** Check Logs
```
n8n: UI → Workflow → Logs
Flask: Terminal output
YouTube: Studio → Videos → Processing status
```

**Step 3:** Test Individually
```
1. Flask health check: curl http://localhost:5000/health
2. Piper: echo "test" | piper --help
3. FFmpeg: ffmpeg -version
4. Google Sheets: Open and verify sheet exists
```

**Step 4:** Nuclear Option
```bash
# Backup your output folder
cp -r D:\piper\output D:\piper\output_backup

# Reset temp (safe to delete)
rm -r D:\piper\temp\*

# Restart everything
python server.py
# (restart n8n in UI)
```

---

## 📈 METRICS TO TRACK WEEKLY

```
Week Ending: ________

Videos Generated: ___  (Target: 4)
Videos Uploaded: ___  (Target: 4)
Total Views: ___  (Target: 2,000+ by week 4)
Avg Watch %: ___%  (Target: 35%+)
Avg CTR: ___%  (Target: 2%+)
Best Performer: ________________
Worst Performer: ________________
Conclusion: ____________________________
```

---

## 🎓 LEARNING RESOURCES

Want to level up? Study these:
- YouTube Algorithm: https://youtube.com/creators
- Psychology content: r/psychology, r/science on Reddit
- Hook writing: "Steal Like an Artist" (Austin Kleon)
- Stoicism: Read Marcus Aurelius "Meditations"

---

**Remember:** Done > Perfect. Ship videos, iterate based on data. 🚀
