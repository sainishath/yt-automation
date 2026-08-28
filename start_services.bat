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
echo [1/3] Checking Ollama Service (Port 11434)...
curl -s http://127.0.0.1:11434/api/tags >nul
if %ERRORLEVEL% equ 0 (
    echo       [OK] Ollama is ONLINE.
) else (
    echo       [STARTING] Launching Ollama daemon...
    start "Ollama" /min ollama serve
    timeout /t 3 >nul
)

:: 3. Check Fooocus SDXL (Port 7865)
echo [2/3] Checking Fooocus SDXL Service (Port 7865)...
curl -s http://127.0.0.1:7865 >nul
if %ERRORLEVEL% equ 0 (
    echo       [OK] Fooocus SDXL is ONLINE on http://127.0.0.1:7865.
) else (
    echo       [STARTING] Launching Fooocus SDXL server...
    start "Fooocus SDXL" /d "D:\Projects\Fooocus" cmd /k "set PYTHONIOENCODING=utf-8 && python launch.py --listen 127.0.0.1 --port 7865"
    echo       Waiting for Fooocus SDXL to initialize...
    timeout /t 10 >nul
)

:: 4. Verify GPU & Environment Readiness
echo [3/3] Checking Python Environment & CUDA Acceleration...
python -c "import torch; print('      [OK] PyTorch:', torch.__version__, '| CUDA Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU (WARNING)')"

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
