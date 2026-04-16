@echo off
chcp 65001 >nul
echo ===============================================
echo   AI 回复逻辑测试前端 - 启动器
echo ===============================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [√] Python 已安装

REM 检查 Flask 是否安装
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [!] Flask 未安装，正在安装...
    pip install flask flask-cors
)

echo [√] Flask 已安装
echo.

REM 启动说明
echo ===============================================
echo   启动说明
echo ===============================================
echo.
echo 1. AI 助手后端服务将启动在：http://localhost:5000
echo 2. 测试页面位置：test_ai_chat.html
echo 3. 按 Ctrl+C 可停止服务
echo.
echo 正在启动后端服务...
echo.

REM 启动后端
cd /d "%~dp0"
start "AI 助手后端服务" python app_api.py

REM 等待 3 秒
timeout /t 3 /nobreak >nul

REM 打开测试页面
echo.
echo [√] 后端服务已启动
echo [√] 正在打开测试页面...
start "" "test_ai_chat.html"

echo.
echo ===============================================
echo   启动完成！
echo ===============================================
echo.
echo 测试页面已打开，可以开始测试 AI 回复逻辑。
echo.
echo 提示：
echo - 在聊天框输入消息测试意图识别
echo - 使用右侧快速测试按钮
echo - 查看分析面板了解意图详情
echo.
echo 按任意键关闭此窗口...
pause >nul
