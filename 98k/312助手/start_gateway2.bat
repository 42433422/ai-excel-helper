@echo off
REM OpenClaw Gateway 启动脚本

echo 启动 OpenClaw Gateway...

set PATH=C:\Users\97088\.trae-cn\binaries\node\versions\22.17.0;%PATH%
set ANTHROPIC_BASE_URL=http://127.0.0.1:5002/v1
set ANTHROPIC_API_KEY=sk-fake-key-not-needed

echo 使用 DeepSeek 包装器: %ANTHROPIC_BASE_URL%
echo.

openclaw gateway --allow-unconfigured --auth none
