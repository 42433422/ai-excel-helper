@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================
:: XCAGI Package Release Script (Windows)
:: Export pre-built Docker images for offline deployment
:: ============================================

echo.
echo ============================================
echo   XCAGI Package Release Tool
echo ============================================
echo.

:: Check parameter
if "%~1"=="" (
    set "VERSION=latest"
) else (
    set "VERSION=%~1"
)

echo Package Version: %VERSION%
echo.

:: Change to script directory
cd /d "%~dp0"

:: Create release-bundle directory
set "RELEASE_DIR=release-bundle"
if exist "%RELEASE_DIR%" (
    echo [WARNING] release-bundle directory exists, deleting...
    rmdir /s /q "%RELEASE_DIR%"
)
mkdir "%RELEASE_DIR%"
echo [OK] Created release-bundle directory

:: 1. Export pre-built images
echo.
echo ============================================
echo Step 1/4: Export pre-built Docker images...
echo ============================================
echo.

:: Check if images exist
docker images redis:7-alpine --format "{{.Repository}}:{{.Tag}}" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] redis:7-alpine not found. Please build images first.
    pause
    exit /b 1
)

echo [INFO] Exporting Docker images to tar files...
echo.

docker save -o "%RELEASE_DIR%\xcagi-redis.tar" redis:7-alpine
if errorlevel 1 (
    echo [ERROR] Failed to export redis image
    pause
    exit /b 1
)
echo [OK] Redis image exported

docker save -o "%RELEASE_DIR%\xcagi-backend.tar" xcagi-backend:latest
if errorlevel 1 (
    echo [ERROR] Failed to export backend image
    pause
    exit /b 1
)
echo [OK] Backend image exported

docker save -o "%RELEASE_DIR%\xcagi-frontend.tar" xcagi-frontend:latest
if errorlevel 1 (
    echo [ERROR] Failed to export frontend image
    pause
    exit /b 1
)
echo [OK] Frontend image exported

docker save -o "%RELEASE_DIR%\xcagi-celery-worker.tar" xcagi-celery-worker:latest
if errorlevel 1 (
    echo [ERROR] Failed to export celery-worker image
    pause
    exit /b 1
)
echo [OK] Celery-worker image exported

echo.
echo [OK] All images exported successfully

:: 2. Copy configuration files
echo.
echo ============================================
echo Step 2/4: Copy configuration files...
echo ============================================
echo.

:: Copy docker-compose configs
copy docker-compose.yml "%RELEASE_DIR%\docker-compose.yml" >nul
copy docker-compose.dev.yml "%RELEASE_DIR%\docker-compose.dev.yml" >nul

:: Copy environment config
if exist ".env.example" (
    copy .env.example "%RELEASE_DIR%\.env.example" >nul
)

:: Create release environment file
echo [INFO] Creating .release.env config...
(
    echo # XCAGI Release Environment Configuration
    echo # Please modify before deployment
    echo.
    echo SECRET_KEY=change-me-before-deployment-%VERSION%
    echo FLASK_ENV=production
    echo LOG_LEVEL=INFO
) > "%RELEASE_DIR%\.release.env"

:: Copy frontend nginx config
if exist "frontend\nginx.conf" (
    mkdir "%RELEASE_DIR%\frontend" 2>nul
    copy "frontend\nginx.conf" "%RELEASE_DIR%\frontend\nginx.conf" >nul
)

:: Copy backend config
if exist "gunicorn_config.py" (
    copy "gunicorn_config.py" "%RELEASE_DIR%\gunicorn_config.py" >nul
)

echo [OK] Configuration files copied

:: 3. Create deployment scripts
echo.
echo ============================================
echo Step 3/4: Create deployment scripts...
echo ============================================
echo.

:: Create Windows deployment script
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo.
    echo :: ============================================
    echo :: XCAGI Offline Deployment Script (Windows)
    echo :: ============================================
    echo.
    echo echo.
    echo echo ============================================
    echo echo   XCAGI Offline Deployment Tool
    echo echo ============================================
    echo echo.
    echo.
    echo :: Check Docker
    echo docker --version ^>nul 2^>^&1
    echo if errorlevel 1 ^(
    echo     echo [ERROR] Please install Docker Desktop first
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo :: Change to script directory
    echo cd /d "%%~dp0"
    echo.
    echo :: Check image files
    echo if not exist "xcagi-redis.tar" ^(
    echo     echo [ERROR] xcagi-redis.tar not found
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo :: Create .env file
    echo if not exist ".env" ^(
    echo     echo [INFO] Creating .env file...
    echo     copy .release.env .env ^>nul
    echo     echo [WARNING] Please edit .env to modify SECRET_KEY
    echo ^)
    echo.
    echo :: Load images
    echo echo Loading Docker images...
    echo docker load -i xcagi-redis.tar
    echo docker load -i xcagi-backend.tar
    echo docker load -i xcagi-frontend.tar
    echo docker load -i xcagi-celery-worker.tar
    echo.
    echo :: Start services
    echo echo Starting services...
    echo docker-compose up -d
    echo.
    echo :: Wait for services
    echo echo Waiting for services to start...
    echo timeout /t 15 /nobreak ^>nul
    echo.
    echo :: Check status
    echo docker-compose ps
    echo.
    echo echo ============================================
    echo echo Deployment completed!
    echo echo ============================================
    echo echo.
    echo echo Access URLs:
    echo echo   Frontend: http://localhost
    echo echo   Backend:  http://localhost:5000
    echo echo.
    echo echo View logs:  docker-compose logs -f
    echo echo Stop:       docker-compose down
    echo echo.
    echo pause
) > "%RELEASE_DIR%\deploy-release.bat"

:: Create Linux deployment script
(
    echo #!/bin/bash
    echo.
    echo # ============================================
    echo # XCAGI Offline Deployment Script (Linux/Mac)
    echo # ============================================
    echo.
    echo set -e
    echo.
    echo echo ""
    echo echo "============================================"
    echo echo "  XCAGI Offline Deployment Tool"
    echo echo "============================================"
    echo echo ""
    echo.
    echo # Check Docker
    echo if ! command -v docker ^&^> /dev/null; then
    echo     echo "[ERROR] Please install Docker first"
    echo     exit 1
    echo fi
    echo.
    echo # Change to script directory
    echo cd "$(dirname "$0")"
    echo.
    echo # Create .env file
    echo if [ ! -f ".env" ]; then
    echo     echo "[INFO] Creating .env file..."
    echo     cp .release.env .env
    echo     echo "[WARNING] Please edit .env to modify SECRET_KEY"
    echo fi
    echo.
    echo # Load images
    echo echo "Loading Docker images..."
    echo docker load -i xcagi-redis.tar
    echo docker load -i xcagi-backend.tar
    echo docker load -i xcagi-frontend.tar
    echo docker load -i xcagi-celery-worker.tar
    echo.
    echo # Start services
    echo echo "Starting services..."
    echo docker-compose up -d
    echo.
    echo # Wait for services
    echo echo "Waiting for services to start..."
    echo sleep 15
    echo.
    echo # Check status
    echo docker-compose ps
    echo.
    echo echo "============================================"
    echo echo "Deployment completed!"
    echo echo "============================================"
    echo echo ""
    echo echo "Access URLs:"
    echo echo "  Frontend: http://localhost"
    echo echo "  Backend:  http://localhost:5000"
    echo echo ""
    echo echo "View logs:  docker-compose logs -f"
    echo echo "Stop:       docker-compose down"
    echo echo ""
) > "%RELEASE_DIR%\deploy-release.sh"

echo [OK] Deployment scripts created

:: 4. Create README
echo.
echo ============================================
echo Step 4/4: Create README...
echo ============================================
echo.

(
    echo # XCAGI Offline Deployment Package
    echo.
    echo ## Package Info
    echo - Version: %VERSION%
    echo - Date: %DATE% %TIME%
    echo.
    echo ## File List
    echo.
    echo ### Image Files
    echo - xcagi-redis.tar - Redis cache service (17MB)
    echo - xcagi-backend.tar - Backend API service (4.5GB)
    echo - xcagi-frontend.tar - Frontend web service (27MB)
    echo - xcagi-celery-worker.tar - Celery async worker (4.5GB)
    echo.
    echo ### Config Files
    echo - docker-compose.yml - Docker Compose config
    echo - docker-compose.dev.yml - Dev environment config
    echo - .env.example - Environment variable example
    echo - .release.env - Release environment variables
    echo.
    echo ### Script Files
    echo - deploy-release.bat - Windows deployment script
    echo - deploy-release.sh - Linux/Mac deployment script
    echo.
    echo ## Deployment Steps
    echo.
    echo ### Windows
    echo 1. Extract package to target machine
    echo 2. Double-click deploy-release.bat
    echo 3. Wait for deployment to complete
    echo 4. Access http://localhost
    echo.
    echo ### Linux/Mac
    echo 1. Extract package to target machine
    echo 2. Run: chmod +x deploy-release.sh
    echo 3. Run: ./deploy-release.sh
    echo 4. Wait for deployment to complete
    echo 5. Access http://localhost
    echo.
    echo ## First Deployment
    echo.
    echo Before deployment, edit .env file:
    echo - SECRET_KEY: Change to random string
    echo - LOG_LEVEL: Set as needed (INFO/WARNING/DEBUG)
    echo.
    echo ## Common Commands
    echo.
    echo # Check status
    echo docker-compose ps
    echo.
    echo # View logs
    echo docker-compose logs -f
    echo.
    echo # Stop services
    echo docker-compose down
    echo.
    echo # Restart services
    echo docker-compose restart
    echo.
    echo ## Access URLs
    echo.
    echo - Frontend: http://localhost
    echo - Backend API: http://localhost:5000
    echo - Health Check: http://localhost:5000/health
    echo - Redis: localhost:6379
    echo.
    echo ## Notes
    echo.
    echo 1. Target machine needs Docker Desktop (Windows) or Docker (Linux/Mac)
    echo 2. Ensure Docker service is running
    echo 3. Ports 80, 5000, 6379 must be available
    echo 4. Image loading takes 5-10 minutes, please wait
    echo 5. Data is stored in Docker volumes, deleting containers will not lose data
    echo.
) > "%RELEASE_DIR%\README.md"

echo [OK] README created

:: 5. Show summary
echo.
echo ============================================
echo Package Summary
echo ============================================
echo.

echo Package Version: %VERSION%
echo Package Directory: %CD%\%RELEASE_DIR%
echo.
echo Package Contents:
echo.

dir "%RELEASE_DIR%" /b
echo.

echo Total Size:
dir "%RELEASE_DIR%" /s | findstr "File(s)"
echo.

echo ============================================
echo Package completed successfully!
echo ============================================
echo.
echo Next steps:
echo 1. Copy release-bundle folder to target machine
echo 2. Run deploy-release.bat (Windows)
echo    or ./deploy-release.sh (Linux/Mac)
echo.
echo See release-bundle\README.md for details.
echo.
pause
