@echo off
where docker >nul 2>nul
if errorlevel 1 (
    echo [INFO] Docker not found. Skip container startup.
    exit /b 0
)

docker info >nul 2>nul
if errorlevel 1 (
    echo [INFO] Docker daemon not running. Skip container startup.
    exit /b 0
)

set "NAME=fhd-xcagi-pg-5433"
docker start %NAME% 1>nul 2>nul
if not errorlevel 1 goto _ok

docker run -d --name %NAME% -e POSTGRES_USER=xcagi -e POSTGRES_PASSWORD=xcagi -e POSTGRES_DB=xcagi -p 5433:5432 postgres:16-alpine >nul
if errorlevel 1 exit /b 1

:_ok
echo [INFO] Postgres container: %NAME%
exit /b 0
