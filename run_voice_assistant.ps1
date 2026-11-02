# Run Jam Desktop Voice Assistant
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "               JAM - Desktop AI Voice Agent             " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Jam is running silently in STANDBY mode." -ForegroundColor Yellow
Write-Host "Wake word: 'Jam', 'Hey Jam', or 'Jam, <command>'" -ForegroundColor Yellow
Write-Host "Background chatter will be ignored silently.`n" -ForegroundColor DarkGray

& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\scripts\voice_assistant.py" $args
