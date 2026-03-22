@echo off
REM 生产环境启动脚本
REM 使用 Gunicorn + Gevent 提供高并发支持

echo 正在启动 XCAGI 生产服务器...

cd /d %~dp0

set FLASK_ENV=production
set XCAGI_DEBUG=0

echo 启动 Gunicorn 服务器（gevent worker）...
python -m gunicorn -c gunicorn_config.py "app:create_app(DevelopmentConfig)"

pause
