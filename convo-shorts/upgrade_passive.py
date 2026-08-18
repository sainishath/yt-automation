import json

file_path = r"./data\yt-automation-workflow.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Update Parse node to be "Smart-Flexible" for AI variations
for node in data["nodes"]:
    if node["name"] == "Parse AI Output":
        node["parameters"]["jsCode"] = """// Expert Smart-Flexible JSON Parser
const items = $input.all();
if (items.length === 0 || !items[0].json) {
  throw new Error('No data from Ollama.');
}

let rawContent = items[0].json.response;
if (!rawContent) {
  throw new Error('Ollama returned empty.');
}

// 1. CLEANUP: AI sometimes returns literal newlines in JSON strings which break JSON.parse
// Replace literal newlines inside strings with escaped \\n
const sanitized = rawContent.replace(/\\n/g, '\\\\n').replace(/\\r/g, '\\\\r');

// 2. EXTRACTION
const firstBrace = sanitized.indexOf('{');
const lastBrace = sanitized.lastIndexOf('}');

if (firstBrace === -1 || lastBrace === -1) {
  throw new Error('No JSON found in response.');
}

const jsonStr = sanitized.substring(firstBrace, lastBrace + 1);

let parsed;
try {
  parsed = JSON.parse(jsonStr);
} catch(e) {
  // If parsing fails, try one more cleanup on common AI screwups
  try {
     const cleaned = jsonStr.replace(/\\"\\s*:\\s*\\[([\\s\\S]*?)\\]/g, (match, p1) => {
        return ':"' + p1.replace(/\\"|'|\\[|\\]/g, '').trim() + '"';
     });
     parsed = JSON.parse(cleaned);
  } catch(e2) {
     throw new Error('Total JSON failure. AI output was too messy.');
  }
}

// 3. FLEXIBLE MAPPING
// Handle if tags is an array or a string
let tags = parsed.tags || '';
if (Array.isArray(tags)) {
  tags = tags.join(', ');
}

return [{
  json: {
    script: parsed.script || 'No script generated',
    title: parsed.title || 'Untitled Video',
    description: parsed.description || '',
    thumbnail_concept: parsed.thumbnail_concept || '',
    tags: tags,
    on_screen_title: (parsed.on_screen_title || 'MIND HACK').toUpperCase(),
    timestamp: new Date().toISOString()
  }
}];"""

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)

print("Smart-Flexible parsing applied.")
