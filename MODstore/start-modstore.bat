@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

start "MODstore API" cmd /k "cd /d ""%~dp0"" && ""%PY%"" -m pip install -q -e ".[web]" && ""%PY%"" -m modstore_server"

echo.
echo API: http://127.0.0.1:8765/api/health
echo.
echo 注意: MODstore 前端已迁移至其他项目，此脚本仅启动 API 服务。
exit /b 0
