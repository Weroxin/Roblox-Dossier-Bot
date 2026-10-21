@echo off
title Roblox Dossier Bot
echo ===========================================
echo       Roblox Dossier Audit Bot Launcher
echo ===========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in your PATH!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b
)

:: Install requirements
echo [1/2] Checking and installing dependencies...
pip install -r requirements.txt
echo.

:: Run bot
echo [2/2] Starting Dossier Bot...
python bot.py
pause