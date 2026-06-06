#requires -Version 5.1
<#
.SYNOPSIS
  Probe FastAPI (phase B): mods/system/auth/ping vs LAN 401 / route 404.

.PARAMETER BaseUrl
  Backend root URL, default http://127.0.0.1:5000

.EXAMPLE
  .\scripts\dev\check_backend_api.ps1
  .\scripts\dev\check_backend_api.ps1 -BaseUrl http://127.0.0.1:8765
#>
param(
    [string]$BaseUrl = 'http://127.0.0.1:5000'
)

$ErrorActionPreference = 'Stop'
$root = $BaseUrl.TrimEnd('/')

function Test-ApiGet {
    param([string]$Path, [int[]]$AcceptCodes)
    $uri = "$root$Path"
    try {
        $resp = Invoke-WebRequest -Uri $uri -Method GET -TimeoutSec 15 -UseBasicParsing
        $code = [int]$resp.StatusCode
    } catch {
        $web = $_.Exception.Response
        if ($null -eq $web) {
            Write-Host "FAIL $Path -> $($_.Exception.Message)" -ForegroundColor Red
            Write-Host '  -> Check backend running, port, firewall.' -ForegroundColor Yellow
            return
        }
        $code = [int]$web.StatusCode.value__
    }
    $ok = $AcceptCodes -contains $code
    $color = if ($ok) { 'Green' } else { 'Yellow' }
    Write-Host "GET $Path -> HTTP $code" -ForegroundColor $color
    if (-not $ok) {
        Write-Host ("  Expected one of: {0}" -f ($AcceptCodes -join ', ')) -ForegroundColor Yellow
        if ($code -eq 401) {
            Write-Host '  -> LAN guard or auth. Check LAN_GUARD_ENABLED; restart backend with new code.' -ForegroundColor Yellow
        }
        if ($code -eq 404) {
            Write-Host '  -> Route missing or wrong process. Use FHD FastAPI + pulled routes.' -ForegroundColor Yellow
        }
    }
}

Write-Host "Probing backend: $root" -ForegroundColor Cyan
Test-ApiGet -Path '/api/ping' -AcceptCodes @(200)
Test-ApiGet -Path '/api/health' -AcceptCodes @(200)
Test-ApiGet -Path '/api/system/industry' -AcceptCodes @(200)
Test-ApiGet -Path '/api/system/industries' -AcceptCodes @(200)
Test-ApiGet -Path '/api/mods/loading-status' -AcceptCodes @(200)
Test-ApiGet -Path '/api/mods/routes' -AcceptCodes @(200)
Test-ApiGet -Path '/api/auth/session/validate' -AcceptCodes @(200)
Write-Host 'Done. If OK here but Vite :5001 fails, fix VITE_API_BASE and restart npm run dev.' -ForegroundColor Cyan
Write-Host 'Note: 401 on /api/mods with x-lan-guard: license-required => old process or wrong repo; 401 without that header => other auth layer.' -ForegroundColor DarkGray
