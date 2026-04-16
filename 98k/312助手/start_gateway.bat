@echo off
REM OpenClaw Gateway 启动脚本 (无认证模式)
REM 使用 DeepSeek API 包装器

echo 启动 OpenClaw Gateway...

set ANTHROPIC_BASE_URL=http://127.0.0.1:5002/v1
set ANTHROPIC_API_KEY=sk-fake-key-not-needed

echo 使用 DeepSeek 包装器: %ANTHROPIC_BASE_URL%
echo 认证模式: none

openclaw gateway --allow-unconfigured --auth none
