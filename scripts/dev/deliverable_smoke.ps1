# Deliverable product smoke (repo root)
param(
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $Root

Write-Host '=== Deliverable Product Smoke ===' -ForegroundColor Cyan

& (Join-Path $PSScriptRoot 'adcdfg_acceptance.ps1') @PSBoundParameters
if ($LASTEXITCODE -ne 0) { throw 'ADCDFG acceptance failed' }

$pyCode = @"
from app.fastapi_app import create_fastapi_app
from fastapi.testclient import TestClient
app = create_fastapi_app()
c = TestClient(app)
h = c.get('/api/health')
assert h.status_code == 200, h.text
d = c.get('/api/platform-shell/deliverable-status').json()
assert d.get('success') is True
data = d.get('data') or {}
assert 'deliverable' in data
assert 'edition' in data
caps = c.get('/api/platform-shell/capabilities').json()
assert caps.get('success') is True
print('deliverable-smoke-ok edition=', data.get('edition'), 'deliverable=', data.get('deliverable'))
"@

python -c $pyCode
if ($LASTEXITCODE -ne 0) { throw 'Deliverable API smoke failed' }
Write-Host '[OK] FastAPI health + deliverable-status + capabilities' -ForegroundColor Green

if (-not $SkipPytest) {
    python -m pytest tests/test_deliverable_status.py tests/test_edition_policy.py -q --tb=short
    if ($LASTEXITCODE -ne 0) { throw 'pytest deliverable failed' }
    Write-Host '[OK] pytest deliverable' -ForegroundColor Green
}

& (Join-Path $PSScriptRoot 'desktop_deliverable_smoke.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Desktop SQLite deliverable smoke failed' }
Write-Host '[OK] desktop SQLite deliverable smoke' -ForegroundColor Green

Write-Host '=== Deliverable Product Smoke PASSED ===' -ForegroundColor Cyan
