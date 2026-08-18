# Growth Security & Secret Governance Manual

---

## 🔒 1. Secret Protection & Exclusion Standards

- All channel profiles in `config/channels/` contain strictly public/non-secret parameters (channel names, handles, audience definitions, categories).
- OAuth credentials (`token.json`, `client_secrets.json`, `youtube_token.pickle`, `youtube_credentials.json`) are strictly excluded by `.gitignore`.
- Pre-commit security scans automatically check `git status` and diffs to prevent accidental credential leakage.
