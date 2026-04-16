#Requires -Version 5.1
<#
.SYNOPSIS
  Run backend pytest; try to start Docker Desktop on Windows so Testcontainers can spin Postgres.

.PARAMETER PytestArgs
  Extra arguments passed to pytest (e.g. "-k", "http_app").
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $PytestArgs = @()
)

$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

function Test-DockerUp {
    try {
        docker info 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

if (-not (Test-DockerUp)) {
    $candidates = @(
        "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe"
    )
    $dd = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if ($dd) {
        Write-Host "Starting Docker Desktop: $dd"
        Start-Process -FilePath $dd -ErrorAction SilentlyContinue
        $deadline = (Get-Date).AddSeconds(120)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 3
            if (Test-DockerUp) {
                Write-Host "Docker is ready."
                break
            }
            Write-Host "Waiting for Docker..."
        }
    }
}

Write-Host ("pytest backend/tests " + ($PytestArgs -join " "))
& python -m pytest backend/tests -q --tb=short @PytestArgs
exit $LASTEXITCODE
