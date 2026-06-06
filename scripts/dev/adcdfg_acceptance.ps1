# ADCDFG acceptance (run from repo root)
param(
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $Root

Write-Host '=== ADCDFG Acceptance ===' -ForegroundColor Cyan

$checks = @()

function Assert-File {
    param([string]$Path, [string]$Label)
    if (Test-Path $Path) {
        $script:checks += @{ ok = $true; label = $Label }
        Write-Host "[OK] $Label" -ForegroundColor Green
    } else {
        $script:checks += @{ ok = $false; label = $Label }
        Write-Host "[FAIL] $Label - missing $Path" -ForegroundColor Red
    }
}

Assert-File -Path 'docs/guides/ADCDFG_COMPLETION_PLAN.md' -Label 'Plan document'
Assert-File -Path 'app/mod_sdk/edition_policy.py' -Label 'Edition policy'
Assert-File -Path 'app/mod_sdk/edition_bootstrap.py' -Label 'Edition bootstrap'
Assert-File -Path 'app/middleware/global_rate_limit.py' -Label 'Global rate limit'

$pyCode = "from app.mod_sdk.decoupling_progress import build_decoupling_progress_payload; from app.mod_sdk.edition_policy import resolve_edition, should_register_host_legacy_routes; import os; os.environ['XCAGI_GENERIC_EDITION']='1'; assert resolve_edition()=='generic'; assert should_register_host_legacy_routes() is False; p=build_decoupling_progress_payload([]); assert p.get('adcdfg_complete') is True; assert p.get('composite_percent')==100; print('python-smoke-ok')"
python -c $pyCode
if ($LASTEXITCODE -ne 0) { throw 'Python smoke failed' }
Write-Host '[OK] Python smoke' -ForegroundColor Green

if (-not $SkipPytest) {
    python -m pytest tests/test_edition_policy.py tests/test_platform_shell.py -q --tb=short
    if ($LASTEXITCODE -ne 0) { throw 'pytest failed' }
    Write-Host '[OK] pytest edition/platform_shell' -ForegroundColor Green
}

$fe = Get-Content 'frontend/package.json' -Raw
if ($fe -notmatch '"build": "vite build --mode generic"') {
    throw 'frontend default build is not generic'
}
Write-Host '[OK] frontend default build:generic' -ForegroundColor Green

$failed = @($checks | Where-Object { -not $_.ok })
if ($failed.Count -gt 0) {
    throw "ADCDFG acceptance failed: $($failed.Count) check(s)"
}
Write-Host '=== ADCDFG Acceptance PASSED ===' -ForegroundColor Cyan
