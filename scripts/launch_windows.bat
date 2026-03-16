@echo off
setlocal

:: Get the directory where the script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

cd /d "%PROJECT_ROOT%"

:: Check for .venv
if not exist ".venv" (
    echo Error: Virtual environment ^(.venv^) not found.
    echo Please run the installation steps in README.md first.
    pause
    exit /b 1
)

:: Run launcher using venv python
:: We use start /b to keep the console window hidden if it opens
".venv\Scripts\python.exe" "src\ibkr_tax\launcher.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo Application failed to start.
    pause
)
