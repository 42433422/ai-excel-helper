@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Default quick-start now uses local dev startup
if exist "%~dp0start-dev.bat" (
    call "%~dp0start-dev.bat"
    exit /b %errorlevel%
)

echo [ERROR] start-dev.bat not found.
pause
exit /b 1
