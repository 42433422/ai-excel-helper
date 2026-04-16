@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

start "ModRepo API" cmd /k "cd /d ""%~dp0"" && ""%PY%"" -m pip install -q -e ".[web]" && ""%PY%"" -m modrepo_server"

timeout /t 2 /nobreak >nul

cd /d "%~dp0modrepo-ui"
if not exist "node_modules\" call npm install
start "ModRepo UI" cmd /k "npm run dev"

echo.
echo UI:  http://127.0.0.1:5173
echo API: http://127.0.0.1:8765/api/health
exit /b 0
