@echo off
chcp 65001 >nul
echo ============================================================
echo DeepSeek MCP Server 快速启动脚本
echo ============================================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python
    pause
    exit /b 1
)

echo [信息] Python 版本检查通过
python --version
echo.

REM 检查依赖是否安装
echo [信息] 检查依赖包...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [警告] 未安装 flask，正在安装依赖...
    pip install -r requirements.txt
) else (
    echo [信息] 依赖包检查通过
)
echo.

REM 启动服务器
echo [信息] 启动 DeepSeek MCP Server...
echo [提示] 按 Ctrl+C 可以停止服务器
echo.
python deepseek_mcp_server.py

pause
