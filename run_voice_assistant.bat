@echo off
title agent-desktop Voice Assistant
echo ========================================================
echo        agent-desktop Free Voice Assistant (Hinglish)
echo ========================================================
echo.
echo Speak into your microphone (e.g., 'Open Chrome', 'List Windows', 'Snapshot Notepad')
echo Press Ctrl+C anytime to stop.
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\voice_assistant.py" %*
pause
