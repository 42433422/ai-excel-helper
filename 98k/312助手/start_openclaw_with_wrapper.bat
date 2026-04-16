@echo off
chcp 65001 >nul
echo ============================================================
echo OpenClaw + DeepSeek Anthropic Wrapper 快速启动
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python
    pause
    exit /b 1
)

echo [信息] Python 版本检查通过
python --version
echo.

REM 设置环境变量
echo [信息] 设置环境变量...
set ANTHROPIC_BASE_URL=http://127.0.0.1:5002/v1
set ANTHROPIC_API_KEY=sk-fake-key-not-needed
echo ANTHROPIC_BASE_URL=%ANTHROPIC_BASE_URL%
echo ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%
echo.

REM 检查 DeepSeek MCP Server
echo [信息] 检查 DeepSeek MCP Server...
curl -s http://127.0.0.1:5001/health >nul 2>&1
if errorlevel 1 (
    echo [警告] DeepSeek MCP Server 未运行
    echo [提示] 请先在另一个窗口启动：python deepseek_mcp_server.py
) else (
    echo [信息] DeepSeek MCP Server 运行正常
)
echo.

REM 检查 Anthropic Wrapper
echo [信息] 检查 Anthropic Wrapper...
curl -s http://127.0.0.1:5002/health >nul 2>&1
if errorlevel 1 (
    echo [警告] Anthropic Wrapper 未运行
    echo [信息] 正在启动 Anthropic Wrapper...
    start "Anthropic Wrapper" cmd /k "cd /d %~dp0 && python deepseek_anthropic_wrapper.py"
    timeout /t 3 /nobreak >nul
) else (
    echo [信息] Anthropic Wrapper 运行正常
)
echo.

REM 启动 OpenClaw Gateway
echo [信息] 启动 OpenClaw Gateway...
echo [提示] 按 Ctrl+C 可以停止 Gateway
echo.
openclaw gateway

pause
