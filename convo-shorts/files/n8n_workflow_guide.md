"""
N8N WORKFLOW: YouTube Shorts Pipeline (Complete Setup)

This workflow:
1. Reads daily topic from Google Sheets
2. Routes to correct Gemini prompt based on category
3. Generates script + hook
4. Sends to Piper TTS for audio
5. Calls Flask backend for video composition
6. Uploads to YouTube
7. Logs results back to Sheets

Prerequisites:
- Google Sheets API credentials
- YouTube API OAuth credentials (you have this)
- n8n with Google Sheets integration
- Your Flask server running locally
"""

# ============================================================================
# WORKFLOW STRUCTURE (Visual)
# ============================================================================

"""
Start (Daily Trigger 9 AM)
    ↓
[Google Sheets] Read Row (Today's Topic + Category)
    ↓
[Switch Node] Check Category
    ├─ Weird Science → Gemini (Science Prompt)
    ├─ Productivity → Gemini (Productivity Prompt)
    └─ Human Behavior → Gemini (Behavior Prompt)
    ↓
[Function Node] Parse [HOOK] [BODY] [CTA]
    ↓
[HTTP Request] Call Flask: POST /generate_video
    Body: {
        "script": body_text,
        "hook": hook_text,
        "cta": cta_text,
        "video_id": unique_id
    }
    ↓
[Wait Node] Wait 5 minutes (video processing)
    ↓
[HTTP Request] YouTube Upload API
    Method: POST
    URL: https://www.googleapis.com/youtube/v3/videos?part=snippet,status
    Headers: Authorization: Bearer {YOUTUBE_TOKEN}
    Body: {
        "snippet": {
            "title": "{HOOK}",
            "description": "{DESCRIPTION}",
            "tags": ["psychology", "facts", "shorts"],
            "categoryId": "27"  // Education category
        },
        "status": {
            "privacyStatus": "public",
            "madeForKids": false
        }
    }
    Media: /path/to/generated/video.mp4
    ↓
[Google Sheets] Update Row
    - YouTube URL
    - Status → "Published"
    - Upload Time
    ↓
End (Notification optional)
"""

# ============================================================================
# NODE CONFIGURATIONS
# ============================================================================

"""
NODE 1: SCHEDULE TRIGGER
Type: Cron
- Time: Every day at 9:00 AM
- Expression: 0 9 * * 1-5 (Monday-Friday)
Output: Timestamp
"""

"""
NODE 2: GOOGLE SHEETS - READ TODAY'S TOPIC
Type: Google Sheets
- Operation: Read
- Sheet Name: "Topics Queue"
- Range: A:J
- Filter: Look for row where Column A matches today's day name (Monday, Tuesday, etc)

Output Example:
{
  "Day": "Monday",
  "Category": "Weird Science",
  "Topic": "Why your brain forgets names",
  "Hook": "",
  "Script Status": "",
  "Video Status": ""
}
"""

"""
NODE 3: SWITCH NODE (Route by Category)
Type: Switch
Conditions:
  Case 1: category == "Weird Science"
    → Route to Gemini (Weird Science Prompt)
  Case 2: category == "Productivity & stoicism"
    → Route to Gemini (Productivity Prompt)
  Case 3: category == "Human Behavior"
    → Route to Gemini (Behavior Prompt)
"""

"""
NODE 4a: GEMINI - WEIRD SCIENCE
Type: AI (Gemini)
Model: gemini-pro
Prompt:
---
You are a science communicator creating a 30-second YouTube Short script.
Topic: {{$json.Topic}}

Generate ONLY a script in this exact format:
[HOOK]
[BODY]
[CTA]

HOOK (2-3 seconds, 10-15 words):
- Start with "Your brain...", "Scientists just...", or "This fact..."
- Make it shocking or unbelievable
- Create immediate curiosity

BODY (20-25 seconds, 80-100 words):
- Explain in simple, conversational language
- Use analogies: "imagine if..." or "think about it like..."
- Include ONE surprising fact
- Sound excited but not over-the-top

CTA (3 seconds, 10-15 words):
- "Drop a 🧠 if you learned something"
- "Follow for more mind-bending facts"
- "Subscribe before your feed changes again"

TONE: Curious, mind-blowing, educational
OUTPUT: Only the script, no other text
---
Temperature: 0.7
Max Tokens: 300
"""

"""
NODE 4b: GEMINI - PRODUCTIVITY
Type: AI (Gemini)
[Similar to 4a, but use PRODUCTIVITY_STOICISM_PROMPT from gemini_prompts.py]
"""

"""
NODE 4c: GEMINI - HUMAN BEHAVIOR
Type: AI (Gemini)
[Similar to 4a, but use HUMAN_BEHAVIOR_PROMPT from gemini_prompts.py]
"""

"""
NODE 5: FUNCTION NODE - PARSE SCRIPT
Type: Function (Code)
Language: JavaScript

Code:
---
const script = $json.response.content[0].text;

// Extract sections using regex
const hookMatch = script.match(/\[HOOK\](.*?)\[BODY\]/s);
const bodyMatch = script.match(/\[BODY\](.*?)\[CTA\]/s);
const ctaMatch = script.match(/\[CTA\](.*?)$/s);

return {
  hook: hookMatch ? hookMatch[1].trim() : "",
  body: bodyMatch ? bodyMatch[1].trim() : "",
  cta: ctaMatch ? ctaMatch[1].trim() : "",
  topic: $json.Topic,
  category: $json.Category,
  videoId: `video_${Date.now()}`
};
---
"""

"""
NODE 6: HTTP REQUEST - CALL FLASK (Generate Video)
Type: HTTP Request
Method: POST
URL: http://localhost:5000/generate_video
Headers: Content-Type: application/json
Body:
{
  "script": "{{$json.body}}",
  "hook": "{{$json.hook}}",
  "cta": "{{$json.cta}}",
  "video_id": "{{$json.videoId}}",
  "audio_speed": 1.15
}

Expected Response:
{
  "status": "success",
  "video_path": "/path/to/video.mp4",
  "thumbnail_path": "/path/to/thumbnail.jpg",
  "duration": 32.5
}
"""

"""
NODE 7: WAIT NODE
Type: Wait
Wait Time: 5 minutes
(This gives Flask time to process video generation)
"""

"""
NODE 8: YOUTUBE UPLOAD
Type: HTTP Request
Method: POST
URL: https://www.googleapis.com/youtube/v3/videos?part=snippet,status,processingDetails

Headers:
  Authorization: Bearer {{$secrets.YOUTUBE_ACCESS_TOKEN}}
  Content-Type: application/json

Body (JSON):
{
  "snippet": {
    "title": "{{$json.hook}} #shorts",
    "description": "{{$json.category}}\n\n{{$json.body}}\n\n#psychology #facts #shorts",
    "tags": [
      "psychology",
      "facts",
      "education",
      "shorts",
      "{{$json.category}}"
    ],
    "categoryId": "27",
    "defaultLanguage": "en",
    "defaultAudioLanguage": "en"
  },
  "status": {
    "privacyStatus": "public",
    "madeForKids": false,
    "selfDeclaredMadeForKids": false
  },
  "processingDetails": {
    "processingProgress": {}
  }
}

File Upload:
- Select "File" mode
- Upload: {{$json.videoPath}} (from Flask response)

Authentication: OAuth 2.0 (use your YouTube credentials)
"""

"""
NODE 9: FUNCTION - EXTRACT VIDEO ID FROM YOUTUBE RESPONSE
Type: Function (Code)

Code:
---
const youtubeResponse = $json.body;
const videoId = youtubeResponse?.id || "PENDING";
const youtubeUrl = `https://youtube.com/shorts/${videoId}`;

return {
  youtubeVideoId: videoId,
  youtubeUrl: youtubeUrl,
  uploadTime: new Date().toISOString()
};
---
"""

"""
NODE 10: GOOGLE SHEETS - UPDATE ROW
Type: Google Sheets
- Operation: Update
- Sheet Name: "Topics Queue"
- Range: Update the row we read from earlier

Update these columns:
- F (Script Status): "Done"
- F (Video Status): "Uploaded"
- G (YouTube URL): "{{$json.youtubeUrl}}"
- Add timestamp

Set "lookup column" to match original Topic so we update the right row
"""

"""
NODE 11: SLACK NOTIFICATION (Optional)
Type: Slack
Message:
🎥 New video uploaded!
Title: {{$json.hook}}
URL: {{$json.youtubeUrl}}
Category: {{$json.category}}
"""

# ============================================================================
# SETUP INSTRUCTIONS
# ============================================================================

"""
STEP 1: Get YouTube Access Token
1. Go to Google Cloud Console
2. Create OAuth 2.0 credentials (Desktop app)
3. Download JSON and save credentials
4. In n8n, create YouTube credentials:
   - Type: OAuth 2.0
   - Client ID: [from JSON]
   - Client Secret: [from JSON]
   - Auth URL: https://accounts.google.com/o/oauth2/v2/auth
   - Access Token URL: https://oauth2.googleapis.com/token
   - Scope: https://www.googleapis.com/auth/youtube.upload

STEP 2: Set up Google Sheets credentials
- Already done if you have Google Sheets integration

STEP 3: Create n8n Secrets
- YOUTUBE_ACCESS_TOKEN: [paste your OAuth token]

STEP 4: Create Google Sheet
- Copy the template from youtube_shorts_template.md
- Share with yourself (edit access)
- Get Sheet ID from URL: docs.google.com/spreadsheets/d/{SHEET_ID}/edit

STEP 5: Build workflow in n8n
- Create new workflow
- Add nodes in order above
- Connect them
- Test with one manual run
- Deploy

STEP 6: Test
- Add a test topic to Google Sheets (e.g., Monday, Weird Science, "Why we yawn")
- Manually trigger workflow
- Watch logs for errors
- Check if video appears on YouTube (unlisted until published)
"""

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
ISSUE: "Video upload fails with 401"
→ YouTube OAuth token expired
→ Solution: Re-authenticate in n8n credentials

ISSUE: "Flask server returns 500"
→ Your server crashed or background folder is empty
→ Solution: Check Flask logs, ensure backgrounds exist

ISSUE: "Gemini returns unformatted text"
→ Model didn't follow prompt format
→ Solution: Increase temperature to 0.8, add stricter instructions

ISSUE: "Video doesn't appear in YouTube Studio"
→ Upload succeeded but processing takes time
→ Wait 15 minutes, refresh YouTube Studio

ISSUE: "Captions are misaligned with audio"
→ Whisper transcription timing is off
→ Solution: Check audio speed (1.15x) vs. video speed
"""
