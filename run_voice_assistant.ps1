# Run agent-desktop Voice Assistant
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       agent-desktop Free Voice Assistant (Hinglish)    " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Speak into your mic: 'Open Chrome', 'List Windows', 'Snapshot Notepad'" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop.`n"

& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\scripts\voice_assistant.py" $args
