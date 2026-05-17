@echo off
setlocal
title social-auto-upload starter

cd /d "%~dp0"

echo Starting social-auto-upload...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-all.ps1"

echo.
echo If the browser did not open, visit:
echo   http://127.0.0.1:5173/
echo.
echo Logs are written to:
echo   backend.out.log
echo   backend.err.log
echo   frontend.out.log
echo   frontend.err.log
echo.
echo To watch backend logs live, run:
echo   watch-logs.bat
echo.
pause
