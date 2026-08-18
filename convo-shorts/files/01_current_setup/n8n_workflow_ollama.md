"""
N8N WORKFLOW: YouTube Shorts Pipeline (100% FREE - Using Ollama)

This workflow:
1. Reads daily topic from Google Sheets
2. Calls Flask /generate_video (which uses Ollama internally)
3. Uploads to YouTube
4. Logs results back to Sheets

NO API CALLS = NO COSTS
"""

# ============================================================================
# SIMPLIFIED WORKFLOW (Much simpler than Gemini version!)
# ============================================================================

"""
Start (Daily 9 AM)
    ↓
[Google Sheets] Read Today's Topic
    ↓
[HTTP Request] Call Flask Generate Video
    ↓
[Wait] 5 minutes (video processing)
    ↓
[HTTP Request] YouTube Upload
    ↓
[Google Sheets] Update Results
    ↓
End
"""

# ============================================================================
# NODE CONFIGURATION
# ============================================================================

"""
NODE 1: SCHEDULE TRIGGER
Type: Cron
Time: 9:00 AM
Days: Monday-Friday
Expression: 0 9 * * 1-5
"""

"""
NODE 2: GOOGLE SHEETS - READ TODAY'S TOPIC
Type: Google Sheets
Operation: Read Rows
Sheet Name: "Topics Queue"
Range: A:J
Filter Logic: Match today's day name (Monday, Tuesday, etc)

Output Variables:
- $json.Day
- $json.Category
- $json.Topic
"""

"""
NODE 3: FUNCTION NODE - EXTRACT TODAY'S ROW
Type: Function (JavaScript)

Code:
---
const data = $json;

// Get today's day name
const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const today = days[new Date().getDay()];

// Find matching row
const todayRow = data.find(row => row['Day'] && row['Day'].trim() === today);

if (!todayRow || !todayRow['Topic']) {
  return {
    error: `No topic found for ${today}`,
    found: false
  };
}

return {
  day: todayRow['Day'],
  category: todayRow['Category'],
  topic: todayRow['Topic'],
  found: true,
  video_id: `video_${Date.now()}`
};
---
"""

"""
NODE 4: HTTP REQUEST - CALL FLASK (Generate Video with Ollama)
Type: HTTP Request
Method: POST
URL: http://localhost:5000/generate_video

Authentication: None
Headers:
  Content-Type: application/json

Body (JSON):
{
  "topic": "{{$json.topic}}",
  "category": "{{$json.category}}",
  "video_id": "{{$json.video_id}}"
}

Expected Response:
{
  "status": "success",
  "video_id": "...",
  "video_path": "/path/to/video.mp4",
  "thumbnail_path": "/path/to/thumb.jpg",
  "script": {
    "hook": "...",
    "body": "...",
    "cta": "..."
  },
  "cost": "$0.00"
}

NOTE: This calls Flask server, which internally uses Ollama (local LLM)
No API calls = No costs!
"""

"""
NODE 5: WAIT NODE
Type: Wait
Wait Time: 5 minutes
(FFmpeg needs time to process video)
"""

"""
NODE 6: HTTP REQUEST - YOUTUBE UPLOAD
Type: HTTP Request
Method: POST
URL: https://www.googleapis.com/youtube/v3/videos?part=snippet,status

Headers:
  Content-Type: application/json
  Authorization: Bearer {{$env.YOUTUBE_ACCESS_TOKEN}}

Body (JSON):
{
  "snippet": {
    "title": "{{$json.body.script.hook}} #shorts",
    "description": "{{$json.body.category}}\n\n{{$json.body.script.body}}\n\n#psychology #facts #shorts",
    "tags": [
      "psychology",
      "facts",
      "education",
      "shorts",
      "{{$json.body.category}}"
    ],
    "categoryId": "27",
    "defaultLanguage": "en"
  },
  "status": {
    "privacyStatus": "public",
    "madeForKids": false,
    "selfDeclaredMadeForKids": false
  }
}

Media Upload:
- Use Media mode
- Upload: {{$json.body.video_path}}
"""

"""
NODE 7: FUNCTION - EXTRACT VIDEO ID
Type: Function (JavaScript)

Code:
---
try {
  const videoId = $json.body.id;
  const youtubeUrl = `https://youtube.com/shorts/${videoId}`;
  
  return {
    videoId: videoId,
    youtubeUrl: youtubeUrl,
    uploadTime: new Date().toISOString(),
    uploadStatus: "success"
  };
} catch (e) {
  return {
    uploadStatus: "pending_processing",
    message: "YouTube may still be processing"
  };
}
---
"""

"""
NODE 8: GOOGLE SHEETS - UPDATE RESULTS
Type: Google Sheets
Operation: Update Rows
Sheet Name: "Topics Queue"

Update Mapping:
- Column E (Script Status): "Done"
- Column F (Video Status): "Uploaded"
- Column G (YouTube URL): "{{$json.youtubeUrl}}"
- Column H (Upload Time): "{{$json.uploadTime}}"

Lookup: Match by "Topic" column to find the right row
"""

"""
NODE 9: SLACK NOTIFICATION (Optional)
Type: Slack
Webhook: [Your Slack webhook URL]

Message:
🎥 New video uploaded!
Topic: {{$json.topic}}
Category: {{$json.category}}
URL: {{$json.youtubeUrl}}
Status: ✅ Processing on YouTube
Cost: $0.00 (100% Free!)
"""

# ============================================================================
# SETUP INSTRUCTIONS
# ============================================================================

"""
STEP 1: Verify Ollama is Running
In terminal:
  ollama serve
  
Then in another terminal:
  ollama pull mistral
  
This downloads Mistral model (~4GB, one-time)

STEP 2: Test Flask Server
python server_ollama.py

Go to: http://localhost:5000/health
Should show:
{
  "status": "ok",
  "ollama_running": true,
  "ollama_model": "mistral"
}

STEP 3: Create n8n Workflow
In n8n:
1. New workflow
2. Add Cron trigger (9 AM daily)
3. Add Google Sheets Read node
4. Add Function node (extract today)
5. Add HTTP Request to Flask
6. Add Wait (5 mins)
7. Add HTTP Request to YouTube
8. Add Function (extract video ID)
9. Add Google Sheets Update
10. Deploy and activate

STEP 4: Set Up YouTube API
In n8n:
1. Admin → Credentials → New
2. Type: OAuth 2.0
3. Fill in your YouTube OAuth credentials
4. In HTTP node, use Bearer token from credentials

STEP 5: Test
Add test topic to Google Sheet:
  Day: Monday
  Category: Weird Science
  Topic: Why you yawn
  
Manually trigger workflow → Watch logs
"""

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================

"""
Create .env file in n8n or set in UI:

YOUTUBE_ACCESS_TOKEN=your_oauth_token_here
FLASK_SERVER_URL=http://localhost:5000

Or hard-code URLs in HTTP nodes.
"""

# ============================================================================
# TESTING WORKFLOW
# ============================================================================

"""
BEFORE GOING LIVE, test each step:

1. Test Ollama:
   curl http://localhost:5000/test_ollama
   
2. Test Flask with manual request:
   curl -X POST http://localhost:5000/generate_video \
     -H "Content-Type: application/json" \
     -d '{
       "topic": "Why we yawn",
       "category": "Weird Science",
       "video_id": "test_video_001"
     }'
   
   Should return video_path in ~3-5 minutes
   
3. Test YouTube upload manually (if video generated)
4. Test full workflow with 1 manual trigger in n8n
5. Check YouTube Studio for uploaded video
"""

# ============================================================================
# COST ANALYSIS
# ============================================================================

"""
COST COMPARISON:

Traditional Approach (Gemini API):
- Per video: ~$0.10 (Gemini) + storage costs
- Monthly (4/week): ~$1.60 + hosting
- Annual: ~$20 + hosting

YOUR APPROACH (Ollama):
- Per video: $0.00
- Monthly: $0.00
- Annual: $0.00
- Only cost: Your electricity (negligible)

SAVINGS: 100% free. Scale infinitely without worrying about costs!
"""

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
ISSUE: "Ollama not running"
FIX: In new terminal, run: ollama serve
    Check model installed: ollama list
    
ISSUE: "HTTP 500 from Flask"
FIX: Check Flask server logs
    Ensure backgrounds folder has videos
    Check Ollama is accessible

ISSUE: "YouTube upload fails"
FIX: Check OAuth token isn't expired
    Re-authenticate credentials in n8n
    
ISSUE: "Script quality is poor"
FIX: Your Ollama model matters
    Try: ollama pull neural-chat (faster)
    Or: ollama pull llama2 (better quality, slower)
    Update OLLAMA_MODEL in server_ollama.py

ISSUE: "Video takes too long"
FIX: Ollama is slower than API
    Wait time depends on your hardware
    Bigger wait = better results
    Adjust wait in Node 5 (5 min recommended)
"""

# ============================================================================
# OPTIMIZATION TIPS
# ============================================================================

"""
To Speed Up Video Generation:

1. Use faster Ollama model:
   - mistral (current, balanced)
   - neural-chat (2x faster, decent quality)
   - dolphin-mixtral (slower, better quality)

2. Reduce audio processing:
   - Remove audio speed (keep at 1.0x)
   - Faster generation, same result

3. Use GPU acceleration:
   - If you have NVIDIA GPU: ollama pull mistral:7b-instruct-q5_K_M
   - Massively faster processing

4. Batch processing:
   - Generate 4 videos at once
   - Run overnight
   - Upload next morning
"""

# ============================================================================
# GROWTH MONITORING
# ============================================================================

"""
Track this in Google Sheets "Analytics" tab:

Week 1 Goals:
- 4 videos uploaded ✓
- 0 API costs ✓
- All automated ✓

Week 2-4 Goals:
- Consistent uploads
- Monitor which topics work
- Note: Growth is slow Week 1-2 (normal)

Month 2:
- Should see 500-2000 views per video
- Identify top-performing category
- Double down on winners
"""
