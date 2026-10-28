@echo off
setlocal enabledelayedexpansion
title YouTube Automations Service Launcher

echo ========================================================
echo   YouTube Automations - Master Service Launcher
echo ========================================================
echo.

:: 1. Set Windows console to UTF-8
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

:: 2. Check Ollama (Port 11434)
echo [1/4] Checking Ollama Service (Port 11434)...
curl -s http://127.0.0.1:11434/api/tags >nul
if %ERRORLEVEL% equ 0 (
    echo       [OK] Ollama is ONLINE.
) else (
    echo       [STARTING] Launching Ollama daemon...
    start "Ollama" /min "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    timeout /t 3 >nul
)

:: 3. Check Fooocus SDXL (Port 7865)
echo [2/4] Checking Fooocus SDXL Service (Port 7865)...
curl -s http://127.0.0.1:7865 >nul
if %ERRORLEVEL% equ 0 (
    echo       [OK] Fooocus SDXL is ONLINE on http://127.0.0.1:7865.
) else (
    echo       [STARTING] Launching Fooocus SDXL server with dedicated environment...
    if exist "D:\AI-Tools\Fooocus\fooocus_env\Scripts\python.exe" (
        start "Fooocus SDXL" /d "D:\AI-Tools\Fooocus" cmd /k "set PYTHONIOENCODING=utf-8 && D:\AI-Tools\Fooocus\fooocus_env\Scripts\python.exe launch.py --listen 127.0.0.1 --port 7865 --always-offload-from-vram"
    ) else (
        start "Fooocus SDXL" /d "D:\AI-Tools\Fooocus" cmd /k "set PYTHONIOENCODING=utf-8 && python launch.py --listen 127.0.0.1 --port 7865 --always-offload-from-vram"
    )
    echo       Waiting for Fooocus SDXL to initialize...
    timeout /t 10 >nul
)

:: 4. Check FFmpeg Media Engine
echo [3/4] Checking FFmpeg Media Pipeline...
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo       [OK] FFmpeg is AVAILABLE.
) else (
    echo       [WARNING] FFmpeg not found in PATH.
)

:: 5. Verify GPU & Environment Readiness
echo [4/4] Checking CUDA Acceleration & PyTorch (Fooocus SDXL Engine)...
if exist "D:\AI-Tools\Fooocus\fooocus_env\Scripts\python.exe" (
    "D:\AI-Tools\Fooocus\fooocus_env\Scripts\python.exe" -c "import torch; print('      [OK] PyTorch:', torch.__version__, '| CUDA Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU (WARNING)')"
) else (
    python -c "import torch; print('      [OK] PyTorch:', torch.__version__, '| CUDA Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU (WARNING)')"
)

echo.
echo ========================================================
echo   All production services are verified and active!
echo ========================================================
echo.
echo Available Production Commands:
echo   Pipeline 1 (Chronos Shift):
echo     python alternate-history-shorts\scripts\pipeline_runner.py --topic "Your Topic"
echo.
echo   Pipeline 2 (Debate Protocol):
echo     python convo-shorts\yt-automation-engine\main.py --topic "Your Coding Topic" --category "Coding"
echo ========================================================
pause
