@echo off
chcp 65001 >nul
setlocal

echo ========================================
echo       Stock Project Setup
echo ========================================
echo.

echo [1/4] Checking Python...
py --version
if errorlevel 1 (
    echo.
    echo ERROR: Python Launcher not found.
    echo Please install Python first.
    pause
    exit /b 1
)

echo.
echo [2/4] Creating virtual environment...

if not exist ".venv\Scripts\python.exe" (
    py -3.14 -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo .venv already exists. Skipping.
)

echo.
echo [3/4] Installing Python packages...

call ".venv\Scripts\activate.bat"

python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install packages.
    pause
    exit /b 1
)

echo.
echo [4/4] Setup completed!
echo.
echo ========================================
echo       Setup successful!
echo ========================================
echo.
echo To start the website:
echo.
echo     .venv\Scripts\activate
echo     python app.py
echo.
pause