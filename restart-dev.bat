@echo off
chcp 65001 >nul

cd /d "%~dp0"

echo.
echo ========================================
echo XCAGI restart: backend 5000 + Vite 5001
echo ========================================
echo.

echo [1/3] Stop listeners on ports 5000 and 5001...
set "PS1=%~dp0restart-dev.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
if errorlevel 1 echo [hint] Close XCAGI Backend / Frontend windows manually if needed.

timeout /t 2 /nobreak >nul

echo.
echo [2/3] Starting backend and frontend...
call "%~dp0start-dev.bat"

exit /b %ERRORLEVEL%
