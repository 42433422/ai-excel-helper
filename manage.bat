@echo off
setlocal

if "%1"=="" goto usage
if "%1"=="dev" goto dev
if "%1"=="stop" goto stop
if "%1"=="deploy" goto deploy
if "%1"=="package" goto package
goto usage

:dev
call start-dev.bat
goto end

:stop
call stop.bat
goto end

:deploy
call deploy.bat
goto end

:package
call package-release.bat
goto end

:usage
echo Usage: manage.bat [dev^|stop^|deploy^|package]
echo.
echo   dev     - Start development server
echo   stop    - Stop all services
echo   deploy  - Deploy to production
echo   package - Package release build

:end
endlocal
