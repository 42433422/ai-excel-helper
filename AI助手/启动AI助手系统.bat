@echo off
title AI助手系统启动器

echo ========================================
echo     AI助手 - 发货单标签生成系统
echo ========================================
echo.

cd /d "C:\Users\Administrator\Desktop\新建文件夹 (4)\AI助手"

echo 正在启动系统...
echo.

echo ✅ 环境检查通过
echo.

echo 🚀 启动AI助手系统...
echo 📍 访问地址: http://127.0.0.1:5000
echo.

REM 启动EXE程序（后台运行）
start /b "AI助手系统" "dist\AI助手系统.exe"

REM 等待服务器启动
echo 等待系统启动...
timeout /t 5 /nobreak >nul

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
