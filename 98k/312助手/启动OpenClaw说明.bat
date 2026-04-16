@echo off
echo ============================================================
echo OpenClaw Gateway 启动脚本
echo ============================================================
echo.
echo 请在新的 PowerShell 窗口中运行以下命令:
echo.
echo ============================================================
echo 步骤 1: 安装 OpenClaw (仅需执行一次)
echo ============================================================
echo.
echo 首先需要在新窗口中安装 OpenClaw。请复制以下命令到新打开的 PowerShell:
echo.
echo     & "C:\Program Files\cursor\resources\app\resources\helpers\npm.cmd" install -g openclaw
echo.
echo ============================================================
echo 步骤 2: 启动 OpenClaw Gateway
echo ============================================================
echo.
echo 安装完成后，运行以下命令启动 Gateway:
echo.
echo     openclaw gateway --port 18789
echo.
echo 然后在浏览器访问: http://localhost:18789
echo.
pause
