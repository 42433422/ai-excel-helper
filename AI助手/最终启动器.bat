@echo off
title AI助手系统启动器

echo ========================================
echo     AI助手 - 发货单标签生成系统
echo ========================================
echo.

cd /d "C:\Users\Administrator\Desktop\新建文件夹 (4)\AI助手"

echo 正在启动系统...
echo.

REM 设置环境变量
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM 检查Python是否存在
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：Python未安装或未添加到PATH
    echo 请确保Python已正确安装
    pause
    exit /b 1
)

REM 检查app_api.py是否存在
if not exist "app_api.py" (
    echo ❌ 错误：app_api.py文件不存在
    pause
    exit /b 1
)

echo ✅ 环境检查通过
echo.

REM 启动Flask服务器（后台运行）
echo 🚀 启动Flask服务器...
echo 📍 访问地址: http://127.0.0.1:5000
echo.

start /b python app_api.py

REM 等待服务器启动
echo 等待服务器启动...
timeout /t 3 /nobreak >nul

REM 自动打开前端页面和数据库管理页面
echo 正在打开前端页面和数据库管理页面...
start http://127.0.0.1:5000
start http://127.0.0.1:5000/database

echo.
echo ✅ 系统启动完成！
echo 🌐 浏览器已自动打开前端和数据库管理页面
echo.
echo 💡 提示：
echo    - 如果浏览器未自动打开，请手动访问: http://127.0.0.1:5000
echo    - 按 Ctrl+C 可停止服务器
echo    - 关闭此窗口将停止系统运行
echo.
echo 系统运行中...
pause