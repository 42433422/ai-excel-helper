@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =============================================
echo FHD 一键启动（Postgres + 环境变量 + API）
echo =============================================

call "%~dp0scripts\docker-postgres-for-fhd.cmd"
if errorlevel 1 (
    echo [WARN] Docker 未拉起 Postgres（未安装 Docker、守护进程未开，或 5432 已被占用）。
    echo        若本机已自行安装 PostgreSQL 并已创建库 xcagi / 用户 xcagi，可忽略本警告。
)

call "%~dp0scripts\fhd-set-database-url.cmd"

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

echo.
echo [FHD] 使用: %PY_EXE%
echo [FHD] 文档/健康检查: http://127.0.0.1:8000/docs
echo.
"%PY_EXE%" -m uvicorn backend.http_app:app --host 127.0.0.1 --port 8000
echo.
if errorlevel 1 echo [ERROR] 后端异常退出（上方面板中的报错多为数据库或依赖问题）。
pause
