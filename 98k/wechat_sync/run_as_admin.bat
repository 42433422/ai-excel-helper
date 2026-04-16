@echo off
chcp 65001 >nul
echo ==========================================
echo   微信数据库密钥提取工具
echo ==========================================
echo.
echo 正在以管理员身份运行...
echo.

:: 检查是否以管理员身份运行
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 请求管理员权限...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo [*] 当前目录: %CD%
echo.

python main.py extract

echo.
echo ==========================================
echo 按任意键退出...
pause >nul
