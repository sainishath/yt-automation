@echo off
set /p topic="Enter your YouTube video topic: "
echo.
echo Launching automation for: %topic%
echo.
curl -X POST http://localhost:5678/webhook-test/generate-video -H "Content-Type: application/json" -d "{\"topic\": \"%topic%\"}"
echo.
echo.
echo Check your n8n tab! The automation should now be running.
pause
