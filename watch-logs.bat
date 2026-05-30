@echo off
setlocal
cd /d "%~dp0"

echo Watching backend logs. Press Ctrl+C to stop.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-Content -Path '.\backend.out.log','.\backend.err.log' -Wait -Tail 80 -ErrorAction SilentlyContinue"
