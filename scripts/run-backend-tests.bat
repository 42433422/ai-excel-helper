@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-backend-tests.ps1" %*
exit /b %ERRORLEVEL%
