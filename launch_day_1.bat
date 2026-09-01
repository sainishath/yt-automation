@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo ============================================================
echo   LAUNCHING DAY 1 PRODUCTION BATCH (6 VIDEOS TOTAL)
echo   Channel A (Chronos Shift): 3 Factual History Shorts
echo   Channel B (Debate Protocol): Lessons 2, 3, 4 (Beginner Python)
echo ============================================================

python daily_scheduler.py --day-1

echo.
echo ============================================================
echo   DAY 1 BATCH GENERATION FINISHED
echo ============================================================
pause
