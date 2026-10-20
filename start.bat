@echo off
chcp 65001 > nul
title Pluxee Enterprise HR Suite - Local Development Server
cd /d "%~dp0"

echo ===============================================================
echo   Pluxee Enterprise HR Suite - Starting Development Environment
echo ===============================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" start_dev.py %*
) else (
    python start_dev.py %*
)

pause
