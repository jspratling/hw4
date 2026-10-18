@echo off
title Campus Customs backend (port 8000)
rem Stops anything already running on port 8000, then starts the FastAPI backend.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%p /F >NUL 2>&1
cd /d "%~dp0backend"
".venv\Scripts\python.exe" -m uvicorn main:app --port 8000
pause
