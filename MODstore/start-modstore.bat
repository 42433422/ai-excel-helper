@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

start "MODstore API" cmd /k "cd /d ""%~dp0"" && ""%PY%"" -m pip install -q -e ".[web]" && ""%PY%"" -m modstore_server"

timeout /t 2 /nobreak >nul

cd /d "%~dp0web"
if not exist "node_modules\" call npm install
start "MODstore UI" cmd /k "npm run dev"

echo.
echo UI:  http://127.0.0.1:5174
echo API: http://127.0.0.1:8765/api/health
exit /b 0
