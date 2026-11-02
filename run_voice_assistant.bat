@echo off
title Jam - Desktop AI Voice Assistant
echo ========================================================
echo                  JAM - Desktop AI Voice Agent
echo ========================================================
echo.
echo Jam is running silently in STANDBY mode.
echo Speak: "Jam", "Hey Jam", or "Jam, <your command>"
echo Background talk without "Jam" will be ignored silently.
echo.
echo Press Ctrl+C anytime to stop.
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\voice_assistant.py" %*
pause
