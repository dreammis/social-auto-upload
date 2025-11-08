@echo off
TITLE One-Click Starter for social-auto-upload

ECHO ==================================================
ECHO  Starting social-auto-upload Servers...
ECHO ==================================================
ECHO.

ECHO [1/2] Starting Python Backend Server in a new window...
REM The START command launches a new process.
REM The first quoted string "SAU Backend" is the title of the new window.
REM cmd /k runs the command and keeps the window open to show logs.
START "SAU Backend" cmd /k "python sau_backend.py"

ECHO [2/2] Starting Vue.js Frontend Server in another new window...
START "SAU Frontend" cmd /k "cd sau_frontend && npm run dev -- --host 0.0.0.0"

ECHO.
ECHO ==================================================
ECHO  Done.
ECHO  Two new windows have been opened for the backend
ECHO  and frontend servers. You can monitor logs there.
ECHO ==================================================
ECHO.

ECHO This window will close in 10 seconds...
timeout /t 10 /nobreak > nul
