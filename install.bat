@echo off
title HacxGPT Installer with venv

echo ======================================
echo     HacxGPT Installer for Windows
echo ======================================

:: ✅ Check for Python
echo [~] Checking for Python...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Python is not installed or not in PATH.
    echo [!] Please install Python from https://www.python.org/downloads/ and make sure to check "Add Python to PATH".
    pause
    exit /b
)
echo [+] Python found.

:: ✅ Clone the repository if needed
if exist "Hacx-GPT" (
    echo [!] Hacx-GPT directory already exists. Skipping clone.
) else (
    echo [+] Cloning Hacx-GPT repository...
    git clone https://github.com/BlackTechX011/Hacx-GPT.git
)

:: ✅ Enter the repo folder
cd Hacx-GPT

:: ✅ Create virtual environment if not exists
if exist ".venv" (
    echo [!] Virtual environment already exists. Skipping creation.
) else (
    echo [+] Creating virtual environment (.venv)...
    python -m venv .venv
)

:: ✅ Activate virtual environment
echo [+] Activating virtual environment...
call .venv\Scripts\activate

:: ✅ Upgrade pip
echo [+] Upgrading pip...
python -m pip install --upgrade pip

:: ✅ Install Python requirements inside venv
echo [+] Installing required python packages in venv...
pip install -r requirements.txt

echo.
echo ======================================
echo       Installation Complete!
echo ======================================
echo To run HacxGPT:
echo.
echo   call .venv\Scripts\activate
echo   python HacxGPT.py
echo.
echo Don't forget to get your API key from OpenRouter or DeepSeek!
echo ======================================
pause
