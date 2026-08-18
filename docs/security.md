# Security Policy & Secret Governance

---

## 🔒 1. Zero-Secret Commitment Standard

Under no circumstances may production secrets, API keys, OAuth tokens, or client credentials be committed to the Git repository.

### Protected File Types
- `token.json`, `youtube_token.pickle`
- `client_secrets.json`, `youtube_credentials.json`
- `.env`, `.env.*`
- Discord bot tokens, webhook secrets
- API tokens (Ollama, OpenAlex, Google Cloud)

---

## 🛡️ 2. .gitignore Protection Rules

The root `.gitignore` enforces exclusion of all credential and runtime artifacts:

```gitignore
# Credentials & Secrets
*.env
.env.*
!.env.example
*token*.json
*token*.pickle
*secret*.json
*credentials*.json
*.pem
*.key

# Runtime Output & Media Assets
output/
data/yt-automation-engine/videos/
data/yt-automation-engine/temp/
temp/
videos/
*.mp4
*.wav
*.mp3
*.webm

# Binaries & Models
*.exe
*.dll
*.onnx
*.ort
*.sqlite
```

---

## 🔍 3. Pre-Commit Security Verification Protocol

Before pushing changes to GitHub, run the automated credential scanner:

```powershell
python -c "
import subprocess
res = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True)
diff = res.stdout.lower()
for term in ['client_secret', 'refresh_token', 'access_token', 'discord_bot_token']:
    if term in diff and 'your_' not in diff and 'placeholder' not in diff:
        raise ValueError(f'Security Alert: Possible credential in diff ({term})')
print('Secret scan passed: 0 credentials found.')
"
```
