@echo off
chcp 65001 >nul
echo ============================================================
echo XCAGI AI 对话系统 - 快速启动脚本
echo ============================================================
echo.

REM 设置 DeepSeek API Key
set DEEPSEEK_API_KEY=sk-5670fc1d73c74f21b4948d7496b7bf16

echo ✓ DeepSeek API Key 已配置
echo.
echo 正在启动 Flask 应用...
echo.

REM 设置 Flask 应用
set FLASK_APP=XCAGI.app:create_app
set FLASK_ENV=development

REM 启动 Flask
python -m flask run --host=0.0.0.0 --port=5000 --debug

echo.
echo 应用已停止
pause
