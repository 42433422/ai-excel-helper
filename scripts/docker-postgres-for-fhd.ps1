#Requires -Version 5.1
<#
.SYNOPSIS
  Start PostgreSQL in Docker with credentials matching backend default DATABASE_URL.

.DESCRIPTION
  User xcagi, databases xcagi + xcagi_test, port 5432.
  If container already exists: docker start. Else: docker run.
  Remove old: docker rm -f fhd-postgres-xcagi

  App default: postgresql+psycopg://xcagi:xcagi@localhost:5432/xcagi
  Tests default: postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi_test
#>
$ErrorActionPreference = "Stop"
$container = "fhd-postgres-xcagi"
$user = "xcagi"
$pass = "xcagi"
$port = "5432"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker not found. Install Docker Desktop and ensure docker is on PATH."
}

docker info 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker daemon is not running. Start Docker Desktop, wait until it is ready, then run this script again."
}

$exists = docker ps -a -q -f "name=$container"
if ($exists) {
    Write-Host "Container exists: $container - starting..."
    docker start $container | Out-Null
} else {
    Write-Host "Creating container $container ..."
    docker run -d `
        --name $container `
        -p "${port}:5432" `
        -e "POSTGRES_USER=$user" `
        -e "POSTGRES_PASSWORD=$pass" `
        -e "POSTGRES_DB=xcagi" `
        postgres:16-alpine | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "docker run failed (see message above)."
    }
    Start-Sleep -Seconds 3
}

Write-Host "Creating database xcagi_test (ignore error if it already exists)..."
docker exec $container psql -U $user -d postgres -c "CREATE DATABASE xcagi_test OWNER $user;" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  (xcagi_test may already exist; continuing)"
}

Write-Host ""
Write-Host "Set before running app or pytest (PowerShell):"
Write-Host '  $env:DATABASE_URL = "postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi"'
Write-Host '  $env:FHD_TEST_DATABASE_URL = "postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi_test"'
Write-Host ""
Write-Host "Stop: docker stop $container"
Write-Host "Remove: docker rm -f $container"
