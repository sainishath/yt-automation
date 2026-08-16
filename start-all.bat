@echo off
title YouTube Automation Server Launcher
color 0A

echo ==================================================
echo    YouTube Automation Stack - Starting Up...
echo ==================================================
echo.

REM ── 1. Start Ollama Server ──
echo [1/4] Starting Ollama Server on port 11434...
start "Ollama Server" /min cmd /k "ollama serve"

REM ── 2. Start Fooocus Image Engine ──
echo [2/4] Starting Fooocus Image Engine on port 7865...
start "Fooocus Image Engine" /min cmd /k "cd /d D:\Projects\Fooocus && set PYTHONIOENCODING=utf-8 && python entry_with_update.py"

REM ── 3. Start Flask Backend (Video Generator) ──
echo [3/5] Starting Flask Video Backend on port 5001...
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
start "Flask Video Backend" /min cmd /k "cd /d yt-automation-engine && python server.py"

REM ── 4. Start Discord Bot Review Listener ──
echo [4/5] Starting Discord Bot Listener...
start "Discord Review Listener" /min cmd /k "cd /d yt-automation-engine && python discord_bot_listener.py"

REM ── 5. Start n8n in Docker ──
echo [5/5] Starting n8n Automation Engine on port 5678...

REM Check if container exists
docker ps -a --format "{{.Names}}" | findstr /i "^n8n$" >nul 2>&1
if %errorlevel% == 0 (
    REM Container exists - just start/restart it
    docker start n8n >nul 2>&1
    if %errorlevel% neq 0 (
        echo    [WARN] Existing container failed, recreating...
        docker rm -f n8n >nul 2>&1
        goto :create_n8n
    )
    echo    [OK] n8n container restarted.
) else (
    :create_n8n
    echo    Creating fresh n8n container...
    docker run -d ^
      --name n8n ^
      --restart unless-stopped ^
      -p 5678:5678 ^
      -u root ^
      -e N8N_BASIC_AUTH_ACTIVE=true ^
      -e N8N_BASIC_AUTH_USER=admin ^
      -e "N8N_BASIC_AUTH_PASSWORD=Zane#6932" ^
      -e N8N_PORT=5678 ^
      -e NODE_ENV=production ^
      -e N8N_RUNNERS_ENABLED=true ^
      -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false ^
      -v "C:\Users\saini\n8n-yt-automation\data:/home/node/.n8n" ^
      n8nio/n8n >nul 2>&1
    echo    [OK] n8n container created.
)

echo.
echo ==================================================
echo    Waiting for services to initialize...
echo ==================================================
timeout /t 15 /nobreak >nul

echo.
echo ==================================================
echo    ALL SYSTEMS GO!
echo ==================================================
echo.
echo    n8n Dashboard  : http://localhost:5678
echo    Flask Backend  : http://localhost:5001
echo.
echo    n8n Login      : admin / Zane#6932
echo.
echo    Flask Endpoints:
echo      POST /tts            - Generate video from script
echo      GET  /get-video      - Download generated final.mp4
echo      POST /upload_youtube - Upload Short to YouTube
echo.
echo    Opening n8n in your browser...
start "" "http://localhost:5678"
echo.
pause
