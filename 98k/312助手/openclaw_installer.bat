@echo off
echo ============================================================
echo OpenClaw Gateway Installer
echo ============================================================
echo.
echo This script will install and run OpenClaw Gateway.
echo.
echo Opening PowerShell window for installation...
echo.

powershell -NoExit -Command "Write-Host '=== OpenClaw Gateway Installation ===' -ForegroundColor Green; Write-Host ''; Write-Host 'Running npm install...' -ForegroundColor Yellow; Write-Host ''; & 'C:\Users\97088\AppData\Local\Programs\cursor\resources\app\resources\helpers\node.exe' 'C:\Users\97088\AppData\Local\Programs\cursor\resources\app\resources\helpers\node_modules\npm\bin\npm-cli.js' install -g openclaw; Write-Host ''; Write-Host 'Installation complete! Now run:' -ForegroundColor Green; Write-Host 'openclaw gateway --port 18789' -ForegroundColor Cyan"

pause
