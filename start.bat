@echo off
chcp 65001 >nul
title XCAGI 智能出货单系统 v3.0

echo =============================================
echo   XCAGI 智能出货单系统
echo   版本: 3.0
echo =============================================
echo.

cd /d "%~dp0"

if exist "XCAGI.exe" (
    echo [启动] 直接运行已打包版本...
    echo.
    echo 请访问: http://localhost:5000
    echo 按 Ctrl+C 停止服务
    echo.
    XCAGI.exe
    goto :end
)

echo [检查] 启动开发环境...
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查前端依赖
if not exist "frontend\node_modules" (
    echo [安装] 前端依赖...
    cd frontend
    call npm install
    cd ..
)

REM 检查数据目录
if not exist "data" (
    mkdir data
)

REM 初始化数据库
echo [初始化] 检查数据库...
python -c "import sqlite3; conn=sqlite3.connect('data/xcagi.db'); conn.close()" 2>nul
if errorlevel 1 (
    echo [初始化] 创建数据库文件...
    python -c "import sqlite3; sqlite3.connect('data/xcagi.db').close()"
)

REM 设置环境变量
set DATABASE_URL=sqlite:///data/xcagi.db
set FLASK_DEBUG=1
set PYTHONUTF8=1

REM 启动后端
echo.
echo [启动] FastAPI 后端服务...
echo 请访问: http://localhost:8000/docs
echo.
python -m uvicorn backend.http_app:app --host 127.0.0.1 --port 8000

:end
pause
