@echo off
title Campus Customs frontend (port 5173)
rem Stops anything already running on port 5173, then starts the Vite dev server.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do taskkill /PID %%p /F >NUL 2>&1
cd /d "%~dp0frontend"
call npm run dev
pause
