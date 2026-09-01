@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo ============================================================
echo   RUNNING DAILY PRODUCTION QUOTA (2 History + 2 Coding)
echo ============================================================

python daily_scheduler.py --daily-quota

echo.
echo ============================================================
echo   DAILY QUOTA RUN FINISHED
echo ============================================================
pause
