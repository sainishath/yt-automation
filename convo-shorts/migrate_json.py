import json
import os

file_path = r"./data\yt-automation-workflow.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# The Ollama HTTP request parameters for the first AI node (Script generation)
node_2_params = {
    "method": "POST",
    "url": "http://host.docker.internal:11434/api/generate",
    "sendHeaders": True,
    "headerParameters": {
        "parameters": [
            {"name": "Content-Type", "value": "application/json"}
        ]
    },
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": """={
  "model": "llama3",
  "stream": false,
  "system": "You are an expert YouTube content strategist with deep knowledge of what makes videos go viral. You specialize in short-form content (YouTube Shorts) that hooks viewers in the first 3 seconds and keeps them watching until the end. You understand psychology, storytelling, pacing, and the YouTube algorithm.\\n\\nYour job is to generate a complete video package:\\n1. A viral video SCRIPT (60-90 seconds of spoken narration, no timecodes, just the words to speak)\\n2. An optimized YouTube TITLE (max 60 chars, curiosity-gap driven, no clickbait that doesn't deliver)\\n3. A compelling DESCRIPTION (first 2 lines hook, then detail, include 3-5 hashtags)\\n4. A THUMBNAIL concept description (vivid, specific, emotional)\\n5. VIDEO TAGS (10-15 comma-separated tags)\\n6. A SHORT TITLE for on-screen display (2-4 words, ALL CAPS)\\n\\nReturn ONLY valid JSON in this exact format:\\n{\\n  \\"script\\": \\"...\\",\\n  \\"title\\": \\"...\\",\\n  \\"description\\": \\"...\\",\\n  \\"thumbnail_concept\\": \\"...\\",\\n  \\"tags\\": \\"...\\",\\n  \\"on_screen_title\\": \\"...\\"\\n}",
  "prompt": "Topic: {{ $json.body.topic }}\\nTarget audience: {{ $json.body.audience || 'general YouTube viewers' }}\\nVideo style: {{ $json.body.style || 'dark psychology / mind-blowing facts' }}\\nChannel niche: {{ $json.body.niche || 'psychology and self-improvement' }}"
}""",
    "options": {
        "timeout": 300000
    }
}

# The Ollama HTTP request parameters for the Viral Clip Selector
node_8_params = {
    "method": "POST",
    "url": "http://host.docker.internal:11434/api/generate",
    "sendHeaders": True,
    "headerParameters": {
        "parameters": [
            {"name": "Content-Type", "value": "application/json"}
        ]
    },
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": """={
  "model": "llama3",
  "stream": false,
  "system": "You are a YouTube Shorts viral clip specialist. Given a video script, identify the single most viral-worthy clip moment (max 45 seconds) that would perform best as a standalone short. Return the start sentence and end sentence of the clip, plus a new punchy title for the short.",
  "prompt": "Script:\\n{{ $('Parse AI Output').item.json.script }}\\n\\nYouTube Video Title: {{ $('Parse AI Output').item.json.title }}\\n\\nReturn JSON:\\n{\\n  \\"clip_start_phrase\\": \\"...\\",\\n  \\"clip_end_phrase\\": \\"...\\",\\n  \\"shorts_title\\": \\"...\\",\\n  \\"shorts_description\\": \\"...\\"\\n}"
}""",
    "options": {
        "timeout": 300000
    }
}

for node in data.get("nodes", []):
    if node["id"] == "b1a2c3d4-0002-0000-0000-000000000002":
        node["name"] = "Ollama Script & Strategy"
        node["type"] = "n8n-nodes-base.httpRequest"
        node["typeVersion"] = 4.2
        node["parameters"] = node_2_params
        if "credentials" in node:
            del node["credentials"]
    
    elif node["id"] == "b1a2c3d4-0008-0000-0000-000000000008":
        node["name"] = "Ollama Viral Clip Selector"
        node["type"] = "n8n-nodes-base.httpRequest"
        node["typeVersion"] = 4.2
        node["parameters"] = node_8_params
        if "credentials" in node:
            del node["credentials"]
            
    # Also need to update the parser nodes to handle Ollama's response structure
    # Ollama returns response under $json.response
    elif node["id"] == "b1a2c3d4-0003-0000-0000-000000000003":  # Parse AI Output
        node["parameters"]["jsCode"] = """// Parse the local Ollama AI response into structured data
const rawContent = $input.first().json.response;

let parsed;
try {
  // Extract JSON from the response (handle code blocks)
  const jsonMatch = rawContent.match(/```(?:json)?\\n?([\\s\\S]*?)\\n?```/) || rawContent.match(/{[\\s\\S]*}/);
  const jsonStr = jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : rawContent;
  parsed = JSON.parse(jsonStr);
} catch(e) {
  throw new Error('Failed to parse AI response: ' + rawContent);
}

return [{
  json: {
    script: parsed.script,
    title: parsed.title,
    description: parsed.description,
    thumbnail_concept: parsed.thumbnail_concept,
    tags: parsed.tags,
    on_screen_title: parsed.on_screen_title || 'MIND HACK',
    timestamp: new Date().toISOString()
  }
}];"""

    elif node["id"] == "b1a2c3d4-0009-0000-0000-000000000009":  # Build Success Report
        node["parameters"]["jsCode"] = """// Build final success report
const ytResult = $('Upload to YouTube').item.json;
const rawClipData = $input.first().json.response;

let clipData;
try {
  const jsonMatch = rawClipData.match(/```(?:json)?\\n?([\\s\\S]*?)\\n?```/) || rawClipData.match(/{[\\s\\S]*}/);
  const jsonStr = jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : rawClipData;
  clipData = JSON.parse(jsonStr);
} catch(e) {
  clipData = { error: 'Failed to parse clip data' };
}

return [{
  json: {
    success: true,
    youtube_video_id: ytResult.id || 'offline_test',
    youtube_url: ytResult.id ? `https://www.youtube.com/watch?v=${ytResult.id}` : null,
    youtube_shorts_url: ytResult.id ? `https://www.youtube.com/shorts/${ytResult.id}` : null,
    title: $('Parse AI Output').item.json.title,
    description: $('Parse AI Output').item.json.description,
    tags: $('Parse AI Output').item.json.tags,
    thumbnail_concept: $('Parse AI Output').item.json.thumbnail_concept,
    viral_clip_suggestion: clipData,
    uploaded_at: new Date().toISOString()
  }
}];"""

# Let's save it as a new ID so it doesn't conflict with the previous import
data["name"] = "YouTube Automation - 100% Free & Local"
data["id"] = "freeFreeYtWkflw"

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Migrated workflow saved.")
