@echo off
setlocal enabledelayedexpansion

REM Deploy from prebuilt images without source code.
cd /d "%~dp0"

set "ARCHIVE="
for %%f in (xcagi-images-*.tar) do (
  set "ARCHIVE=%%f"
  goto found_archive
)

:found_archive
if "%ARCHIVE%"=="" (
  echo Could not find xcagi-images-*.tar in current directory.
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" (
    copy .env.example .env >nul
    echo Created .env from .env.example. Please update SECRET_KEY.
  ) else (
    echo Missing .env and .env.example.
    exit /b 1
  )
)

if exist ".release.env" (
  for /f "usebackq tokens=1,* delims==" %%a in (".release.env") do (
    if not "%%a"=="" set "%%a=%%b"
  )
)

echo [1/4] Loading images from %ARCHIVE% ...
docker load -i "%ARCHIVE%" || exit /b 1

echo [2/4] Stopping previous containers ...
docker-compose down >nul 2>&1

echo [3/4] Starting services ...
docker-compose up -d || exit /b 1

echo [4/4] Current status ...
docker-compose ps

echo.
echo Deployment complete.
echo Frontend: http://localhost
echo Backend health: http://localhost:5000/health
echo.
