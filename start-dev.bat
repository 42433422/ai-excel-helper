@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ========================================
echo FHD: XCAGI 桌面交付模式（SQLite + Vite）
echo ========================================
echo [INFO] Web/PostgreSQL 开发请用: XCAGI\start-xcagi.bat 或 xcagi-backend.cmd
echo.

echo [1/2] Starting desktop backend at http://127.0.0.1:5000 ...
start "XCAGI Desktop Backend" /D "%~dp0XCAGI" cmd /k "call ""%~dp0XCAGI\xcagi-backend-desktop.cmd"""

set "FRONTEND_DIR=%~dp0frontend"
if not exist "%FRONTEND_DIR%\package.json" (
  if exist "%~dp0XCAGI\frontend\package.json" (
    set "FRONTEND_DIR=%~dp0XCAGI\frontend"
  )
)
if not exist "%FRONTEND_DIR%\package.json" (
  echo [WARN] frontend\package.json not found, skip frontend.
  goto done
)

echo [2/2] Starting frontend at http://127.0.0.1:5001 ...
start "XCAGI Frontend" /D "%FRONTEND_DIR%" cmd /k "npm run dev"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5001/"

:done
echo.
echo [OK] Startup command executed.
echo Backend : http://127.0.0.1:5000  (desktop SQLite)
echo API Docs: http://127.0.0.1:5000/docs
echo Frontend: http://127.0.0.1:5001/
echo.
exit /b 0
