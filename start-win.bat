@echo off
setlocal
title One-Click Starter for social-auto-upload
cd /d "%~dp0"

if not defined SAU_WEB_HOST set "SAU_WEB_HOST=127.0.0.1"
if not defined SAU_WEB_PORT set "SAU_WEB_PORT=5409"

if /I not "%SAU_WEB_HOST%"=="127.0.0.1" if /I not "%SAU_WEB_HOST%"=="localhost" (
  echo ERROR: SAU_WEB_HOST must be 127.0.0.1 or localhost.
  exit /b 1
)

where uv >nul 2>&1
if errorlevel 1 (
  if exist "%~dp0..\.tools\uv\uv.exe" (
    set "PATH=%~dp0..\.tools\uv;%PATH%"
  ) else (
    echo ERROR: uv was not found. Install uv or provide ..\.tools\uv\uv.exe.
    exit /b 1
  )
)

where npm >nul 2>&1
if errorlevel 1 (
  echo ERROR: npm was not found.
  exit /b 1
)

set "VITE_API_PROXY_TARGET=http://%SAU_WEB_HOST%:%SAU_WEB_PORT%"

echo [1/2] Starting the locked Python Web backend on %SAU_WEB_HOST%:%SAU_WEB_PORT%...
start "SAU Backend" cmd /k "cd /d ""%~dp0"" && uv run --extra web --frozen python sau_backend.py"

echo [2/2] Starting the Vue frontend on 127.0.0.1...
start "SAU Frontend" cmd /k "cd /d ""%~dp0sau_frontend"" && npm run dev -- --host 127.0.0.1"

echo Both local service windows have been opened.
endlocal
